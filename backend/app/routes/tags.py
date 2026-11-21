"""C3 Tag routes: /api/tags, /api/tags/suggest, /api/admin/tags"""

from flask import Blueprint, jsonify, request

from app.errors import BadRequest
from app.models import TagType
from app.schemas import TagAdminUpdate, TagCreate
from app.security import current_user, login_required, roles_required
from app.services import tag_service
from app.services.dto import tag_dto
from app.utils import parse_body

bp = Blueprint("tags", __name__, url_prefix="/api")


def _type_arg():
    value = request.args.get("type")
    if not value:
        return None
    try:
        return TagType(value)
    except ValueError:
        raise BadRequest("type must be one of: domain, expertise, tool, skill.")


@bp.get("/tags")
def list_tags():
    """Approved tags. Public, because the registration page needs them before sign-in."""
    return jsonify([tag_dto(t) for t in tag_service.list_tags(_type_arg())])


@bp.post("/tags/suggest")
@login_required
def suggest():
    tag = tag_service.suggest(parse_body(TagCreate), current_user())
    return jsonify(tag_dto(tag, include_status=True)), 201


@bp.get("/admin/tags")
@roles_required("admin")
def admin_list():
    return jsonify([tag_dto(t, include_status=True) for t in tag_service.list_tags(_type_arg(), include_pending=True)])


@bp.post("/admin/tags")
@roles_required("admin")
def admin_create():
    return jsonify(tag_dto(tag_service.admin_create(parse_body(TagCreate)), include_status=True)), 201


@bp.patch("/admin/tags/<int:tag_id>")
@roles_required("admin")
def admin_update(tag_id):
    tag = tag_service.admin_update(tag_id, parse_body(TagAdminUpdate))
    if tag is None:
        return jsonify({"message": "Suggestion rejected and removed.", "id": tag_id})
    return jsonify(tag_dto(tag, include_status=True))
