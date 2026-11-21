"""C16 Scheduler jobs (partial - Sprint 1).

Implemented now:
* expire pending requests past ``expires_on``      (also run lazily before every request operation)
* end mentorships 15 days after a one-sided end request

Run them with ``flask --app app run-jobs`` (e.g. from Windows Task Scheduler / cron
once a day). A built-in background scheduler is deliberately NOT started inside the
web process: with Flask's auto-reloader that would run every job twice (the master
prompt asks that jobs are never duplicated). Remaining jobs - stuck-request
reminders, completing sessions, purging accounts - are Sprint 2.
"""

from app.services import mentoring_service, request_service


def run_all() -> dict:
    return {
        "expired_requests": request_service.expire_due_requests(),
        "auto_ended_mentorships": mentoring_service.auto_end_due(),
    }
