"""Import every model so ``db.create_all()`` sees all tables."""

from app.models.activities import (
    Availability, Feedback, MentoringSession, PlatformFeedback, ReportUser, SessionActionItem, TrackGoal,
)
from app.models.enums import *  # noqa: F401,F403
from app.models.mentoring import Mentorship, Request, RequestStatusHistory
from app.models.notifications import Notification
from app.models.tags import Tag, UserTag
from app.models.user import Mentor, Student, User

__all__ = [
    "Availability", "Feedback", "MentoringSession", "PlatformFeedback", "ReportUser", "SessionActionItem",
    "TrackGoal", "Mentorship", "Request", "RequestStatusHistory", "Notification", "Tag", "UserTag",
    "Mentor", "Student", "User",
]
