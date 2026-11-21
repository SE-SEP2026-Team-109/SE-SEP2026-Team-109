"""Authentication and authorisation helpers (M2 shared mechanisms).

* Password hashing  - bcrypt (never store plain text).
* JWT guard         - ``@login_required`` validates the Bearer token, loads the user
                      into ``g.current_user`` and returns 401 if missing/expired.
* Role guard        - ``@roles_required("admin")`` returns 403 for other roles.

The participant guard (404 for records you are not part of) lives in each
service, because only the service knows who the participants of a record are.
"""

from datetime import datetime, timedelta, timezone
from functools import wraps

import bcrypt
import jwt
from flask import current_app, g, request

from app.errors import Forbidden, Unauthorized
from app.extensions import db


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: int, role: str) -> tuple[str, datetime]:
    expires = datetime.now(timezone.utc) + timedelta(minutes=current_app.config["JWT_EXPIRE_MINUTES"])
    payload = {"sub": str(user_id), "role": role, "exp": expires}
    token = jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm=current_app.config["JWT_ALGORITHM"])
    return token, expires


def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=[current_app.config["JWT_ALGORITHM"]])
        return int(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise Unauthorized("Your session has expired. Please sign in again.")
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise Unauthorized("Invalid authentication token.")


def _load_current_user():
    from app.models import User  # local import avoids a circular import

    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise Unauthorized("Authentication required.")
    user_id = decode_access_token(header.removeprefix("Bearer ").strip())
    user = db.session.get(User, user_id)
    if user is None:
        raise Unauthorized("Invalid authentication token.")
    if not user.is_active:
        # Deactivated, blacklisted or to-be-deleted users lose access immediately (M2 C1).
        raise Unauthorized("This account is no longer active.")
    return user


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        g.current_user = _load_current_user()
        return view(*args, **kwargs)

    return wrapper


def roles_required(*roles: str):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            user = _load_current_user()
            if user.role.value not in roles:
                raise Forbidden("You do not have permission to perform this action.")
            g.current_user = user
            return view(*args, **kwargs)

        return wrapper

    return decorator


def current_user():
    return g.current_user
