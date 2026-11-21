"""C13 Notifications.

M2 rule: other components call ``notify(...)`` INSIDE their own transaction and
never write the table themselves; users only ever see their own notifications.
"""

from app import repositories as repo
from app.errors import NotFound
from app.extensions import db
from app.models import Notification, UserRole, utcnow


def notify(uid: int, message: str, link: str | None = None, rid: int | None = None) -> None:
    """Add a notification to the current transaction. The caller commits."""
    db.session.add(Notification(uid=uid, message=message, link=link, rid=rid))


def notify_role(role: UserRole, message: str, link: str | None = None) -> None:
    for user in repo.users_with_role(role):
        notify(user.id, message, link)


def list_for(user) -> list[Notification]:
    return repo.notifications_for(user.id)


def mark_read(user, notification_id: int) -> Notification:
    n = db.session.get(Notification, notification_id)
    if n is None or n.uid != user.id:  # 404, not 403, so ids cannot be probed
        raise NotFound("Notification not found.")
    if n.marked_on is None:
        n.marked_on = utcnow()
        db.session.commit()
    return n


def mark_all_read(user) -> int:
    count = 0
    for n in repo.notifications_for(user.id):
        if n.marked_on is None:
            n.marked_on = utcnow()
            count += 1
    db.session.commit()
    return count
