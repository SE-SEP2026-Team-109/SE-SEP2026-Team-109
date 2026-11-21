
"""Shared notification utilities used by application services."""

from sqlalchemy.orm import Session

from app.models.notifications import Notification


def notify(
    db: Session,
    uid: int,
    message: str,
) -> None:
    """
    Add a notification for a user within the current transaction.

    The caller is responsible for committing or rolling back the
    transaction. This allows notifications to be persisted atomically
    with the business operation that generated them.

    Args:
        db: Active SQLAlchemy database session.
        uid: ID of the user receiving the notification.
        message: Notification message to display.
    """
    notification = Notification(
        uid=uid,
        message=message,
    )

    db.add(notification)
