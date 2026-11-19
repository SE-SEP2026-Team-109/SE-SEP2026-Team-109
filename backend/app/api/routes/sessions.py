"""API routes for mentoring sessions."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.database import get_db
from app.models.user import User
from app.schemas.sessions import (
    SessionCreate,
    SessionDecision,
    SessionRead,
    SessionReschedule,
)
from app.services import session_service

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
def create_session(
    data: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return session_service.create_session(db, current_user, data)


@router.get("/", response_model=list[SessionRead])
def get_my_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return session_service.get_my_sessions(db, current_user)


@router.get("/{session_id}", response_model=SessionRead)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return session_service.get_session_by_id(db, current_user, session_id)


@router.patch("/{session_id}/respond", response_model=SessionRead)
def respond_to_session(
    session_id: int,
    data: SessionDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return session_service.respond_to_session(
        db, current_user, session_id, data
    )


@router.patch("/{session_id}/reschedule", response_model=SessionRead)
def reschedule_session(
    session_id: int,
    data: SessionReschedule,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return session_service.reschedule_session(
        db, current_user, session_id, data
    )


@router.patch("/{session_id}/cancel", response_model=SessionRead)
def cancel_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return session_service.cancel_session(db, current_user, session_id)


@router.patch("/{session_id}/complete", response_model=SessionRead)
def complete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return session_service.complete_session(db, current_user, session_id)