"""Smaller blueprints: health check, C6 mentoring, C13 notifications, admin (Sprint 1 part)."""

from flask import Blueprint, jsonify

from app.schemas import VerificationUpdate
from app.security import current_user, login_required, roles_required
from app.services import admin_service, mentoring_service, notification_service
from app.services.dto import mentorship_dto, notification_dto, user_dto
from app.utils import parse_body, query_bool

bp = Blueprint("misc", __name__, url_prefix="/api")


@bp.get("/health")
def health():
    return jsonify({"status": "ok"})


# ---------------- C6 Mentoring ----------------

@bp.get("/mentoring")
@login_required
def list_mentoring():
    user = current_user()
    items = mentoring_service.list_for(user, include_ended=bool(query_bool("include_ended")))
    return jsonify([mentorship_dto(ms, user) for ms in items])


@bp.post("/mentoring/<int:mentoring_id>/end")
@roles_required("student", "mentor")
def end_mentoring(mentoring_id):
    user = current_user()
    return jsonify(mentorship_dto(mentoring_service.request_end(user, mentoring_id), user))


@bp.post("/mentoring/<int:mentoring_id>/end/cancel")
@roles_required("student", "mentor")
def cancel_end(mentoring_id):
    user = current_user()
    return jsonify(mentorship_dto(mentoring_service.cancel_end(user, mentoring_id), user))


# ---------------- C13 Notifications ----------------

@bp.get("/notifications")
@login_required
def list_notifications():
    return jsonify([notification_dto(n) for n in notification_service.list_for(current_user())])


@bp.patch("/notifications/<int:notification_id>/read")
@login_required
def mark_read(notification_id):
    return jsonify(notification_dto(notification_service.mark_read(current_user(), notification_id)))


@bp.patch("/notifications/read-all")
@login_required
def mark_all_read():
    return jsonify({"updated": notification_service.mark_all_read(current_user())})


# ---------------- Admin (Sprint 1 part of C14) ----------------

@bp.get("/admin/users")
@roles_required("admin")
def admin_users():
    admin = current_user()
    return jsonify([user_dto(u, admin) for u in admin_service.list_users()])


@bp.patch("/admin/mentors/<int:mentor_id>/verification")
@roles_required("admin")
def verify_mentor(mentor_id):
    data = parse_body(VerificationUpdate)
    admin = current_user()
    return jsonify(user_dto(admin_service.set_verification(mentor_id, data.status), admin))
