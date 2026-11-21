"""C4 Mentor Directory route: GET /api/mentors"""

from flask import Blueprint, jsonify, request

from app.errors import BadRequest
from app.security import current_user, roles_required
from app.services import directory_service
from app.services.dto import user_dto
from app.utils import query_bool, query_int

bp = Blueprint("mentors", __name__, url_prefix="/api")

SORT_ALIASES = {"match": "best_match", "slots": "free_slots", "exp": "experience"}


@bp.get("/mentors")
@roles_required("student", "coordinator", "admin")
def directory():
    sort = request.args.get("sort", "best_match")
    sort = SORT_ALIASES.get(sort, sort)
    if sort not in directory_service.SORTS:
        raise BadRequest("sort must be best_match, free_slots or experience.")
    viewer = current_user()
    result = directory_service.search(
        viewer,
        q=request.args.get("q") or None,
        industry=request.args.get("industry") or None,
        area=request.args.get("area") or None,
        expertise=request.args.get("expertise") or None,
        has_slots=query_bool("has_slots"),
        sort=sort,
        page=query_int("page", 1),
        page_size=query_int("page_size", 20, maximum=100),
    )
    items = []
    for m in result["items"]:
        dto = user_dto(m, viewer, active_counts=result["counts"])
        dto["can_request"] = (viewer.role.value == "student" and not result["student_has_active_mentorship"]
                              and dto["mentor"]["free_slots"] > 0)
        items.append(dto)
    return jsonify({k: v for k, v in result.items() if k not in ("items", "counts")} | {"items": items})
