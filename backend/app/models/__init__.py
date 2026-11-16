"""Import every model module so Base.metadata sees all tables before create_all() runs."""

from app.models.availability import Availability
from app.models.feedback import Feedback, PlatformFeedback
from app.models.goals import TrackGoal
from app.models.mentoring import Mentorship, Request
from app.models.notifications import Notification
from app.models.reports import ReportUser
from app.models.sessions import MentoringSession, SessionActionItem
from app.models.tags import Tag, UserTag
from app.models.user import Mentor, Student, User, UserRole

__all__ = [
    "Availability",
    "Feedback",
    "PlatformFeedback",
    "TrackGoal",
    "Mentorship",
    "Request",
    "Notification",
    "ReportUser",
    "MentoringSession",
    "SessionActionItem",
    "Tag",
    "UserTag",
    "Mentor",
    "Student",
    "User",
    "UserRole",
]

