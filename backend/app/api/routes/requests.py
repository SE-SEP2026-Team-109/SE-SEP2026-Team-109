"""API routes for mentoring requests."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.database import get_db
from app.models.enums import RequestStatus
from app.models.user import User
from app.schemas.requests import (
    RequestCreate,
    RequestDecision,
    RequestRead,
)
from app.services.request_service import (
    create_request,
    decide_request,
    get_request,
    list_requests,
    withdraw_request,
)


router = APIRouter(prefix="/requests", tags=["requests"])


@router.post("", response_model=RequestRead, status_code=201)
def create_mentoring_request(
    data: RequestCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a mentoring request as a student or assigned request as a coordinator/admin."""
    return create_request(db, current_user, data)


@router.get("", response_model=list[RequestRead])
def read_requests(
    request_status: RequestStatus | None = Query(
        default=None,
        alias="status",
        description="Filter requests by status.",
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List the authenticated student's requests or mentor's incoming requests."""
    return list_requests(db, current_user, request_status)


@router.get("/{request_id}", response_model=RequestRead)
def read_request(
    request_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve a request belonging to the authenticated participant."""
    return get_request(db, current_user, request_id)


@router.post("/{request_id}/withdraw", response_model=RequestRead)
def withdraw_mentoring_request(
    request_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Withdraw a pending request submitted by the authenticated student."""
    return withdraw_request(db, current_user, request_id)


@router.post("/{request_id}/decision", response_model=RequestRead)
def decide_mentoring_request(
    request_id: int,
    data: RequestDecision,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Accept or reject a pending request as its assigned mentor."""
    return decide_request(db, current_user, request_id, data)