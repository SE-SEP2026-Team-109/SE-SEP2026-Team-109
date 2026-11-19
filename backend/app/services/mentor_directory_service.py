import math

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.enums import (
    MentorshipStatus,
    TagType,
    UserRole,
    UserStatus,
    VerificationStatus,
)
from app.models.mentoring import Mentorship, Request
from app.models.tags import Tag, UserTag
from app.models.user import Mentor, User

from app.schemas.mentor_directory import (
    DirectoryTagRead,
    MentorDirectoryItem,
    MentorDirectoryResponse,
)



def get_mentor_directory(
    db: Session,
    current_user: User,
    q: str | None = None,
    industry: str | None = None,
    area: str | None = None,
    expertise: str | None = None,
    has_slots: bool | None = None,
    sort: str = "free_slots",
    page: int = 1,
    page_size: int = 20,
):
    """
    Retrieve verified mentors with filtering, sorting and pagination.

    Filter mapping:
    - industry: domain tags
    - area: expertise tags
    - expertise: skill or tool tags

    Free slots are calculated as capacity minus active mentorships.
    Paused mentors remain visible but cannot receive new requests.
    """

    # Count active mentorships for each mentor.
    active_counts = (
        db.query(
            Request.mid.label("mentor_id"),
            func.count(Mentorship.id).label("active_count"),
        )
        .join(Mentorship, Mentorship.rid == Request.id)
        .filter(Mentorship.status == MentorshipStatus.active)
        .group_by(Request.mid)
        .subquery()
    )

    active_count = func.coalesce(active_counts.c.active_count, 0)
    free_slots = Mentor.capacity - active_count

    # Only active users with verified mentor profiles appear in the directory.
    query = (
        db.query(
            User,
            Mentor,
            active_count.label("active_count"),
        )
        .join(Mentor, Mentor.id == User.id)
        .outerjoin(active_counts, active_counts.c.mentor_id == Mentor.id)
        .options(
            selectinload(User.user_tags).joinedload(UserTag.tag)
        )
        .filter(
            User.status == UserStatus.active,
            Mentor.veri_status == VerificationStatus.verified,
        )
    )

    # Search across the mentor's name, designation and company.
    if q:
        search_term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                User.name.ilike(search_term),
                Mentor.designation.ilike(search_term),
                Mentor.company.ilike(search_term),
            )
        )

    # Check whether a mentor has an approved tag matching the filter.
    def tag_filter(tag_types, value):
        """Create a correlated filter for a mentor's approved tags."""

        matching_tag = (
            db.query(UserTag.uid)
            .join(Tag, Tag.id == UserTag.tag_id)
            .filter(
                UserTag.uid == User.id,
                Tag.t_status.is_(True),
                Tag.type.in_(tag_types),
                Tag.name.ilike(f"%{value.strip()}%"),
            )
            .exists()
        )

        return matching_tag

    if industry:
        query = query.filter(
            tag_filter([TagType.domain], industry)
        )

    if area:
        query = query.filter(
            tag_filter([TagType.expertise], area)
        )

    if expertise:
        query = query.filter(
            tag_filter([TagType.skill, TagType.tool], expertise)
        )

    # Filter by calculated free slots, not by the stored capacity alone.
    if has_slots is True:
        query = query.filter(free_slots > 0)
    elif has_slots is False:
        query = query.filter(free_slots <= 0)

    # Count matching mentors before applying pagination.
    total = query.order_by(None).count()

    # A student who already has an active mentorship cannot request another.
    student_has_active_mentorship = False

    if current_user.role == UserRole.student:
        student_has_active_mentorship = (
            db.query(Mentorship.id)
            .join(Request, Request.id == Mentorship.rid)
            .filter(
                Request.sid == current_user.id,
                Mentorship.status == MentorshipStatus.active,
            )
            .first()
            is not None
        )

    # Retrieve the filtered results.
    if sort == "free_slots":
        query = query.order_by(
            free_slots.desc(),
            User.name.asc(),
        )
        results = query.offset((page - 1) * page_size).limit(page_size).all()

    elif sort == "experience":
        query = query.order_by(
            Mentor.experience.desc().nullslast(),
            User.name.asc(),
        )
        results = query.offset((page - 1) * page_size).limit(page_size).all()

    elif sort == "best_match":
        # Best match compares the mentor's selected tags with the
        # current user's selected tags.
        current_tag_ids = {
            user_tag.tag_id
            for user_tag in current_user.user_tags
        }

        # Retrieve all filtered mentors so matching can be ranked
        # before pagination is applied.
        results = query.all()

        def match_score(result):
            mentor_user, mentor, occupied = result

            mentor_tag_ids = {
                user_tag.tag_id
                for user_tag in mentor_user.user_tags
                if user_tag.tag and user_tag.tag.t_status
            }

            return len(current_tag_ids.intersection(mentor_tag_ids))

        results.sort(
            key=lambda result: (
                match_score(result),
                result[1].capacity - result[2],
            ),
            reverse=True,
        )

        start = (page - 1) * page_size
        results = results[start:start + page_size]

    else:
        raise ValueError("Unsupported mentor directory sort option.")

    # Convert database records into the public directory response.
    items = []

    for mentor_user, mentor, occupied in results:
        occupied = int(occupied)
        available_slots = max(mentor.capacity - occupied, 0)

        # A request is enabled only for a student when the mentor
        # has capacity, is not paused, and the student has no active mentor.
        can_request = (
            current_user.role == UserRole.student
            and not student_has_active_mentorship
            and not mentor.pause
            and available_slots > 0
        )

        mentor_tags = [
            DirectoryTagRead.model_validate(user_tag.tag)
            for user_tag in mentor_user.user_tags
            if user_tag.tag and user_tag.tag.t_status
        ]

        items.append(
            MentorDirectoryItem(
                id=mentor.id,
                name=mentor_user.name,
                photo=mentor_user.photo,
                designation=mentor.designation,
                company=mentor.company,
                bio=mentor.bio,
                experience=mentor.experience,
                capacity=mentor.capacity,
                free_slots=available_slots,
                is_paused=mentor.pause,
                can_request=can_request,
                tags=mentor_tags,
            )
        )

    return MentorDirectoryResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total else 0,
    )

