"""C5 Request routes: /api/requests"""

from flask import Blueprint, jsonify, request

from app.errors import BadRequest
from app.models import RequestStatus
from app.schemas import RequestCreate, RequestDecision
from app.security import current_user, login_required
from app.services import request_service
from app.services.dto import request_dto
from app.utils import parse_body

bp = Blueprint("requests", __name__, url_prefix="/api/requests")


@bp.post("")
@login_required
def create():
    data = parse_body(RequestCreate)
    user = current_user()
    req = request_service.create(user, data.mentor_id, data.student_message, data.student_id)
    return jsonify(request_dto(req, user)), 201


@bp.get("")
@login_required
def list_requests():
    status = request.args.get("status")
    try:
        status = RequestStatus(status) if status else None
    except ValueError:
        raise BadRequest("Unknown request status.")
    user = current_user()
    return jsonify([request_dto(r, user) for r in request_service.list_for(user, status)])


@bp.get("/<int:request_id>")
@login_required
def get_one(request_id):
    user = current_user()
    return jsonify(request_dto(request_service.get_for(user, request_id), user))


@bp.post("/<int:request_id>/withdraw")
@login_required
def withdraw(request_id):
    user = current_user()
    return jsonify(request_dto(request_service.withdraw(user, request_id), user))


@bp.post("/<int:request_id>/decision")
@login_required
def decide(request_id):
    data = parse_body(RequestDecision)
    user = current_user()
    return jsonify(request_dto(request_service.decide(user, request_id, data.action, data.reason), user))
