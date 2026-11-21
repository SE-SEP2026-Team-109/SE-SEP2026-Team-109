# MentorConnect backend (Flask)

Flask + SQLAlchemy + SQLite + JWT REST API for MentorConnect (IITM BS SE, Team 109).
Architecture: Milestone 2 modular monolith, with routes → services → repositories → models.

## Quick start
```powershell
python -m venv venv
venv\Scripts\activate            # macOS/Linux: source venv/bin/activate
pip install -r requirements-dev.txt
copy .env.example .env           # then set SECRET_KEY
python run.py                    # http://127.0.0.1:5000/api/health
```
The first start creates `instance/mentorconnect.db` with demo data (password `Demo1234`, see `app/seed.py`).

## Commands
| Command | What it does |
|---|---|
| `python run.py` | Development server on port 5000 (auto-reload) |
| `python -m pytest` | Run the test suite (in-memory DB, never touches your data) |
| `flask --app app init-db` | Create missing tables (keeps data) |
| `flask --app app seed-demo` | Insert demo data if the DB has no users |
| `flask --app app run-jobs` | Scheduled jobs once: expire overdue requests, auto-end mentorships (schedule daily with cron/Task Scheduler) |
| `flask --app app reset-db --yes` | **Deletes all data**, then recreates and seeds the database |

## Layout
```
app/
  __init__.py        create_app() factory, blueprints, CLI
  config.py          settings + all business limits
  extensions.py      SQLAlchemy object
  errors.py          AppError classes + JSON error handlers
  security.py        bcrypt, JWT, @login_required, @roles_required
  schemas.py         Pydantic request validation
  repositories.py    shared queries
  models/            tables (user, tags, mentoring, notifications, activities = Sprint 2 tables)
  services/          auth, profile, tag, directory, request, mentoring, notification, admin, jobs, dto
  routes/            auth, profile, tags, mentors, requests, misc (health, mentoring, notifications, admin)
  seed.py            demo data
tests/               pytest suite (53 tests)
```

Documentation: `../docs/` (architecture, API reference, components, testing, traceability, decisions, handover).
