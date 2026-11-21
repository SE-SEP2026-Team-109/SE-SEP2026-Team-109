"""Enumerations used by the models.

Ported from the FastAPI ``app/models/enums.py`` (which mirrors the team's DBML
schema). Changes are marked "CHANGE" and recorded in docs/decisions.md.
"""

import enum
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Naive UTC 'now'. All timestamps are stored in UTC and sent to the frontend with a 'Z' suffix."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class UserRole(str, enum.Enum):
    admin = "admin"
    student = "student"
    mentor = "mentor"
    coordinator = "coordinator"


class Course(str, enum.Enum):
    data_science_and_applications = "data_science_and_applications"
    electronic_systems = "electronic_systems"
    aeronautics_and_space_technology = "aeronautics_and_space_technology"
    management_and_data_science = "management_and_data_science"


class CourseLevel(str, enum.Enum):
    diploma = "diploma"
    bsc_degree = "bsc_degree"
    bs_degree = "bs_degree"


class StudentType(str, enum.Enum):
    standalone = "standalone"
    dual_degree = "dual_degree"
    full_time_working_professional = "full_time_working_professional"
    part_time_working_professional = "part_time_working_professional"


class UserStatus(str, enum.Enum):
    active = "active"
    deactive = "deactive"
    blacklisted = "blacklisted"
    to_be_deleted = "to_be_deleted"


class VerificationStatus(str, enum.Enum):
    pending = "pending"
    verified = "verified"
    rejected = "rejected"


class MentorAvailabilityStatus(str, enum.Enum):
    available = "available"
    unavailable = "unavailable"
    in_a_session = "in_a_session"


class RequestStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    expired = "expired"
    withdrawn = "withdrawn"
    closed_by_admin = "closed_by_admin"


class RequestSource(str, enum.Enum):
    student = "student"
    coordinator = "coordinator"


class TrackGoalStatus(str, enum.Enum):
    todo = "todo"  # CHANGE: added (M2 minutes, Meeting 7; also added on the team's FastAPI 'goals' branch)
    in_progress = "in_progress"
    done = "done"
    delete = "delete"


class SessionStatus(str, enum.Enum):
    pending = "pending"
    scheduled = "scheduled"
    rescheduled = "rescheduled"
    cancelled = "cancelled"
    completed = "completed"
    declined = "declined"  # CHANGE: added so a declined booking is distinguishable from a cancellation


class GoalVisibility(str, enum.Enum):
    public = "public"
    mentors = "mentors"
    private = "private"
    mentorship_only = "mentorship_only"


class TagType(str, enum.Enum):
    domain = "domain"
    expertise = "expertise"
    tool = "tool"
    skill = "skill"


class ReportStatus(str, enum.Enum):
    pending = "pending"
    resolved = "resolved"
    dismissed = "dismissed"
    in_review = "in_review"


class ReportCategory(str, enum.Enum):
    inappropriate_language = "inappropriate_language"
    harassment = "harassment"
    mentor_stopped_replying = "mentor_stopped_replying"
    asking_for_personal_favours = "asking_for_personal_favours"
    privacy_concern = "privacy_concern"
    others = "others"


class MentorshipStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    pending = "pending"


class FeedbackKind(str, enum.Enum):  # CHANGE: new - frontend has session and final feedback
    session = "session"
    final = "final"
