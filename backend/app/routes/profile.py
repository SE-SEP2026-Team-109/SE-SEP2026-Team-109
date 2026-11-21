"""C2 Profile routes: /api/profile/me, /api/mentors/<id>, /api/students/<id>/card"""

from flask import Blueprint, jsonify

from app.schemas import ProfileTagsUpdate, ProfileUpdate
from app.security import current_user, login_required, roles_required
from app.services import profile_service
from app.services.dto import user_dto
from app.utils import parse_body

bp = Blueprint("profile", __name__, url_prefix="/api")


@bp.get("/profile/me")
@login_required
def get_me():
    user = current_user()
    return jsonify(user_dto(user, user))


@bp.put("/profile/me")
@login_required
def update_me():
    user = profile_service.update_profile(current_user(), parse_body(ProfileUpdate))
    return jsonify(user_dto(user, user))


@bp.put("/profile/me/tags")
@login_required
def update_my_tags():
    user = profile_service.set_tags(current_user(), parse_body(ProfileTagsUpdate))
    return jsonify(user_dto(user, user))


@bp.get("/mentors/<int:mentor_id>")
@roles_required("student", "coordinator", "admin")
def mentor_profile(mentor_id):
    viewer = current_user()
    return jsonify(user_dto(profile_service.public_mentor(viewer, mentor_id), viewer))


@bp.get("/students/<int:student_id>/card")
@roles_required("mentor", "coordinator", "admin")
def student_card(student_id):
    viewer = current_user()
    return jsonify(user_dto(profile_service.student_card(viewer, student_id), viewer))
