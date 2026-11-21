"""C4 Mentor Directory: search, filter, sort and paginate verified mentors.

Ported from FastAPI ``services/mentor_directory_service.py``. Rules (M2 C4):
* only active users with a VERIFIED mentor profile are listed;
* free slots = capacity - active mentorships (computed, not stored);
* paused mentors stay visible (frontend shows a "Paused" badge) but cannot be requested;
* sort by best match (shared tags), most free places, or most experience.
CHANGE: industry / career area are mentor columns (the frontend collects them as
fields), and also match domain/expertise tags as in the FastAPI version.
"""

import math

from sqlalchemy import select

from app import repositories as repo
from app.extensions import db
from app.models import Mentor, User, UserRole, UserStatus, VerificationStatus

SORTS = {"best_match", "free_slots", "experience"}


def search(viewer: User, q=None, industry=None, area=None, expertise=None, has_slots=None,
           sort="best_match", page=1, page_size=20) -> dict:
    stmt = (
        select(User).join(Mentor, Mentor.id == User.id)
        .where(User.role == UserRole.mentor, User.status == UserStatus.active,
               Mentor.veri_status == VerificationStatus.verified)
    )
    mentors = list(db.session.scalars(stmt))
    counts = repo.active_mentorship_counts()

    def tag_names(u, types=None):
        return [ut.tag.name.lower() for ut in u.user_tags
                if ut.tag and ut.tag.t_status and (types is None or ut.tag.type.value in types)]

    def contains(value, candidates):
        v = value.strip().lower()
        return any(v == c or v in c for c in candidates if c)

    if q:  # name, role, company, bio or a tag ("topic"), as the frontend search box promises
        term = q.strip().lower()
        mentors = [m for m in mentors if any(term in (s or "").lower() for s in
                   [m.name, m.mentor.designation, m.mentor.company, m.mentor.bio, *tag_names(m)])]
    if industry:
        mentors = [m for m in mentors if contains(industry, [(m.mentor.industry or "").lower()] + tag_names(m, {"domain"}))]
    if area:
        mentors = [m for m in mentors if contains(area, [(m.mentor.career_area or "").lower()] + tag_names(m, {"expertise"}))]
    if expertise:
        mentors = [m for m in mentors if contains(expertise, tag_names(m))]

    def free(m):
        return 0 if m.mentor.pause else max(0, m.mentor.capacity - counts.get(m.id, 0))

    if has_slots is True:
        mentors = [m for m in mentors if free(m) > 0]
    elif has_slots is False:
        mentors = [m for m in mentors if free(m) <= 0]

    viewer_tags = {ut.tag_id for ut in viewer.user_tags}
    if sort == "free_slots":
        mentors.sort(key=lambda m: (-free(m), m.name or ""))
    elif sort == "experience":
        mentors.sort(key=lambda m: (-(m.mentor.experience or 0), m.name or ""))
    else:  # best_match: number of shared tags, then free places
        mentors.sort(key=lambda m: (-len(viewer_tags & {ut.tag_id for ut in m.user_tags}), -free(m), m.name or ""))

    total = len(mentors)
    start = (page - 1) * page_size
    student_has_mentor = viewer.role == UserRole.student and repo.active_mentorship_for_student(viewer.id) is not None
    return {
        "items": mentors[start:start + page_size],
        "counts": counts,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if total else 0,
        "student_has_active_mentorship": student_has_mentor,
    }
