
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.profile import ProfileRead, ProfileUpdate, MentorPublicProfileRead
from app.services.profile_service import (
    get_user_profile, 
    update_user_profile,
    get_public_mentor_profile
)

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/me", response_model=ProfileRead)
def read_my_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    profile = get_user_profile(db, current_user.id)

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found",
        )

    return profile


@router.put("/me", response_model=ProfileRead)
def update_my_profile(
    updates: ProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        updated_profile = update_user_profile(db, current_user, updates)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return updated_profile


mentor_router = APIRouter(prefix="/mentors", tags=["mentors"])

@mentor_router.get("/{mentor_id}", response_model=MentorPublicProfileRead)
def read_public_mentor_profile(
    mentor_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in {
        UserRole.student,
        UserRole.coordinator,
        UserRole.admin,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to view public mentor profiles",
        )

    mentor_user = get_public_mentor_profile(db, mentor_id)

    if mentor_user is None or mentor_user.mentor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mentor profile not found",
        )

    mentor = mentor_user.mentor

    return {
        "id": mentor_user.id,
        "name": mentor_user.name,
        "photo": mentor_user.photo,
        "iitm_program": mentor.iitm_program,
        "level_completed": mentor.level_completed,
        "year_completed": mentor.year_completed,
        "designation": mentor.designation,
        "bio": mentor.bio,
        "company": mentor.company,
        "experience": mentor.experience,
        "capacity": mentor.capacity,
        "pause": mentor.pause,
    }