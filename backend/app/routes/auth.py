"""C1 Auth routes: /api/auth/*"""

from flask import Blueprint, jsonify, request

from app.schemas import ChangePasswordIn, LoginIn, RegisterIn
from app.security import current_user, login_required
from app.services import auth_service
from app.services.dto import user_dto
from app.utils import iso, parse_body

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.post("/register")
def register():
    user = auth_service.register(parse_body(RegisterIn))
    return jsonify(user_dto(user, user)), 201


@bp.post("/login")
def login():
    # JSON {"email", "password"}. Form fields username/password are also accepted so the
    # earlier FastAPI-style client (OAuth2 form) keeps working.
    if request.is_json:
        data = parse_body(LoginIn)
    else:
        data = LoginIn(email=request.form.get("username") or request.form.get("email") or "",
                       password=request.form.get("password") or "")
    user, token, expires = auth_service.login(data.email, data.password)
    return jsonify({"access_token": token, "token_type": "bearer", "expires_at": iso(expires.replace(tzinfo=None)),
                    "user": user_dto(user, user)})


@bp.get("/me")
@login_required
def me():
    user = current_user()
    return jsonify(user_dto(user, user))


@bp.post("/change-password")
@login_required
def change_password():
    data = parse_body(ChangePasswordIn)
    auth_service.change_password(current_user(), data.current_password, data.new_password)
    return jsonify({"message": "Password changed."})


@bp.post("/logout")
@login_required
def logout():
    # JWTs are stateless: the client deletes its token. This endpoint exists so the
    # frontend has one clear "sign out" call and the server can log it later if needed.
    return jsonify({"message": "Signed out."})
