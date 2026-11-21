"""Error handling (M2 shared mechanism "Error handler").

Services raise ``AppError`` subclasses instead of returning HTTP responses, so the
service layer never knows about HTTP. The handlers below turn them into a single
JSON shape that the frontend understands:

    {"error": {"status": 409, "message": "...", "details": [...]}}

``detail`` is also included because the existing frontend api.js (written for
FastAPI) reads ``body.detail``.
"""

import logging

from flask import jsonify
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

log = logging.getLogger(__name__)


class AppError(Exception):
    status = 400

    def __init__(self, message: str, details=None, status: int | None = None):
        super().__init__(message)
        self.message = message
        self.details = details
        if status is not None:
            self.status = status


class BadRequest(AppError):
    status = 400


class Unauthorized(AppError):
    status = 401


class Forbidden(AppError):
    status = 403


class NotFound(AppError):
    status = 404


class Conflict(AppError):
    status = 409


def error_body(status: int, message: str, details=None):
    body = {"error": {"status": status, "message": message}, "detail": message}
    if details:
        body["error"]["details"] = details
    return jsonify(body), status


def _pydantic_details(exc: ValidationError):
    out = []
    for err in exc.errors():
        field = ".".join(str(p) for p in err.get("loc", ()))
        msg = err.get("msg", "Invalid value").removeprefix("Value error, ")
        out.append({"field": field, "message": msg})
    return out


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(exc: AppError):
        return error_body(exc.status, exc.message, exc.details)

    @app.errorhandler(ValidationError)
    def handle_validation(exc: ValidationError):
        details = _pydantic_details(exc)
        first = details[0] if details else {"field": "", "message": "Invalid input"}
        label = first["field"].replace("_", " ")
        message = f"{label}: {first['message']}" if label else first["message"]
        return error_body(400, message, details)

    @app.errorhandler(HTTPException)
    def handle_http(exc: HTTPException):
        return error_body(exc.code or 500, exc.description or exc.name)

    @app.errorhandler(SQLAlchemyError)
    def handle_db(exc: SQLAlchemyError):
        from app.extensions import db

        db.session.rollback()
        log.exception("Database error")
        return error_body(500, "A database error occurred. Please try again.")
