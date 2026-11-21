"""Response DTOs ("data transfer objects").

M2 rule: routes return DTOs, never raw models - so the password hash can never
leak, and privacy masking is a single mapping step. Every API response that
contains a user goes through ``user_dto``.

Masking rule (US-02/US-08, M2 C2 "Profile masking"): email and phone are shown to
* the user themself,
* an administrator,
* a student/mentor pair once a request between them has been ACCEPTED.
Everyone else gets ``null``.
"""

from app import repositories as repo
from app.models import Notification, Request, Tag, User, UserRole
from app.utils import iso


def can_see_contact(viewer: User | None, subject: User) -> bool:
    if viewer is None:
        return False
    if viewer.id == subject.id or viewer.role == UserRole.admin:
        return True
    pair = {viewer.role, subject.role}
    if pair == {UserRole.student, UserRole.mentor}:
        sid, mid = (viewer.id, subject.id) if viewer.role == UserRole.student else (subject.id, viewer.id)
        return repo.accepted_request_between(sid, mid)
    return False


def tag_dto(tag: Tag, include_status: bool = False) -> dict:
    out = {"id": tag.id, "name": tag.name, "type": tag.type.value if tag.type else None}
    if include_status:
        out["approved"] = bool(tag.t_status)
    return out


def user_dto(user: User, viewer: User | None = None, active_counts: dict | None = None) -> dict:
    show = can_see_contact(viewer, user)
    out = {
        "id": user.id,
        "role": user.role.value,
        "name": user.name,
        "username": user.username,
        "email": user.email if show else None,
        "phone": user.phone if show else None,
        "photo": user.photo,
        "status": user.status.value,
        "created_at": iso(user.created_at),
        "delete_time": iso(user.delete_time),
        "tags": [
            {**tag_dto(ut.tag), "want_to_learn": ut.want_to_learn, "skill_level": ut.skill_level}
            for ut in user.user_tags if ut.tag is not None and ut.tag.t_status
        ],
        "student": None,
        "mentor": None,
    }
    if user.role == UserRole.student and user.student is not None:
        s = user.student
        out["student"] = {
            "course": s.course.value if s.course else None,
            "courselevel": s.courselevel.value if s.courselevel else None,
            "type": s.type.value if s.type else None,
            "careergoal": s.careergoal,
            "rollno": s.rollno if show else None,
            "mneeds": s.mneeds,
            "skills": s.skills or [],
        }
    if user.role == UserRole.mentor and user.mentor is not None:
        m = user.mentor
        active = (active_counts or {}).get(user.id) if active_counts is not None else repo.count_active_mentorships(user.id)
        active = active or 0
        out["mentor"] = {
            "designation": m.designation,
            "company": m.company,
            "experience": m.experience,
            "industry": m.industry,
            "career_area": m.career_area,
            "support_types": m.support_types or [],
            "bio": m.bio,
            "capacity": m.capacity,
            "pause": m.pause,
            "veri_status": m.veri_status.value if m.veri_status else None,
            "iitm_program": m.iitm_program.value if m.iitm_program else None,
            "level_completed": m.level_completed.value if m.level_completed else None,
            "year_completed": m.year_completed,
            "still_enrolled": m.still_enrolled,
            "linkedin": m.linkedin,
            "active_mentees": active,
            "free_slots": 0 if m.pause else max(0, m.capacity - active),
        }
    return out


def history_dto(entry) -> dict:
    return {
        "from": entry.from_status.value if entry.from_status else None,
        "to": entry.to_status.value,
        "actor": entry.actor_role,
        "at": iso(entry.changed_on),
    }


def request_dto(req: Request, viewer: User, include_message: bool = True) -> dict:
    """Admins and coordinators never see the private request message (M2 Meeting 5, decision 2)."""
    staff = viewer.role in (UserRole.admin, UserRole.coordinator)
    return {
        "id": req.id,
        "sid": req.sid,
        "mid": req.mid,
        "status": req.status.value,
        "created_on": iso(req.created_on),
        "changed_on": iso(req.changed_on),
        "expires_on": iso(req.expires_on),
        "student_message": None if (staff or not include_message) else req.student_message,
        "mentor_response": None if staff else req.mentor_response,
        "req_source": req.req_source.value,
        "assigned_by": req.assigned_by,
        "history": [history_dto(h) for h in req.history],
        "student": user_dto(req.student.user, viewer) if req.student else None,
        "mentor": user_dto(req.mentor.user, viewer) if req.mentor else None,
    }


def mentorship_dto(ms, viewer: User) -> dict:
    req = ms.request
    return {
        "id": ms.id,
        "rid": ms.rid,
        "sid": req.sid,
        "mid": req.mid,
        "status": ms.status.value,
        "start": iso(ms.start),
        "end": iso(ms.end),
        "student_end_requested_at": iso(ms.student_end_requested_at),
        "mentor_end_requested_at": iso(ms.mentor_end_requested_at),
        "assigned_by": req.assigned_by,
        "student": user_dto(req.student.user, viewer),
        "mentor": user_dto(req.mentor.user, viewer),
    }


def notification_dto(n: Notification) -> dict:
    return {
        "id": n.id,
        "message": n.message,
        "link": n.link,
        "read": n.marked_on is not None,
        "created_at": iso(n.created_at),
        "rid": n.rid,
    }
