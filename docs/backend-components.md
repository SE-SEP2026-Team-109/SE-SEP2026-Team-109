# Backend components (C1–C16)

One section per Milestone 2 component: what it does, which files implement it, the important
functions and rules, and its honest status. For endpoint details see [api-reference.md](api-reference.md).
FastAPI references point to `legacy/fastapi_backend/app/...`.

**Status legend:** ✅ implemented and tested · 🟡 partial · ⏳ Sprint 2 (tables exist, no API).

---

## Shared foundation (used by every component)

| File | Why it exists |
|---|---|
| `app/__init__.py` | **Application factory** `create_app()`. Each call builds a fresh app (tests use this to get an empty in-memory database). It loads config, connects SQLAlchemy, enables CORS for `/api/*`, registers the blueprints and error handlers, creates missing tables, seeds demo data when the DB is empty, and adds the CLI commands `init-db`, `seed-demo`, `reset-db --yes`, `run-jobs`. It also turns on SQLite foreign keys and a 5-second busy timeout. |
| `app/config.py` | Settings from environment/`.env`, plus **every business limit** in one place (14 days, 3 pending, 50–1500, 500, 5/6 tags, capacity 1–10, 15 days, IITM domain). `TestConfig` uses an in-memory DB. |
| `app/extensions.py` | The single `db = SQLAlchemy(...)` object, using SQLAlchemy 2.0 typed models (same style as the FastAPI models, so they ported almost unchanged). |
| `app/errors.py` | `AppError` and subclasses (`BadRequest` 400, `Unauthorized` 401, `Forbidden` 403, `NotFound` 404, `Conflict` 409). Services raise these; handlers turn them, Pydantic validation errors and database errors into one JSON format. |
| `app/security.py` | bcrypt hashing; JWT create/decode (PyJWT, HS256, 120 min, `sub` = user id); decorators `@login_required` and `@roles_required(...)`. They return 401 for a missing/expired token or an inactive account, and 403 for the wrong role. |
| `app/schemas.py` | Pydantic request schemas, reused from the FastAPI shapes with the M1 rules added (password strength, capacity 1–10, optional reject reason). |
| `app/repositories.py` | The M2 "queries that enforce rules": count pending requests, count active mentorships, active mentorship for a student, overdue pending requests, `lock_mentor` (SQLite-safe lock, D-15), tag lookups, notifications. |
| `app/services/dto.py` | Converts models to JSON. `can_see_contact()` implements email/phone masking (D-12). `request_dto` hides message text from staff (D-13). |
| `app/utils.py` | `iso()` UTC timestamps with `Z`, `parse_body()` validation helper, query-string helpers. |
| `app/seed.py` | Demo data mirroring the old `mock.js` (see decisions P-06). |

---

## C1 Auth ✅ (US-01)
**Files:** `routes/auth.py`, `services/auth_service.py` (ported from FastAPI `api/routes/auth.py`, where the logic sat in the route).
* `register(data)`: checks the IITM domain for students, duplicate email/username (409), hashes the password, creates `users` + `student`/`mentor` in **one transaction** (flush to get the id, then commit or roll back), attaches approved interest/expertise tags, marks new mentors `pending` and notifies admins.
* `login(email, password)`: the same 401 message for unknown email or wrong password (so it does not reveal which); 403 with a clear message for deactivated, blacklisted or to-be-deleted accounts. Returns the JWT and expiry.
* `change_password(...)`: verifies the current password and applies the strength rule.
* Logout: the client discards the token (`POST /auth/logout` exists for a clear flow).

## C2 Profile ✅ (US-02, US-03, US-04)
**Files:** `routes/profile.py`, `services/profile_service.py` (ported from FastAPI `services/profile_service.py` + route logic).
* `update_profile`: partial update of common, student and mentor fields. Username uniqueness (409). Photo must be `https://` or `data:image/…` and ≤ 400 KB (D-11). Mentors can change `capacity` (1–10) and **`pause`** (D-03). Students can clear the course level ("Foundation").
* `set_tags`: replaces the tag selection. Approved tags only; students ≤ 5, mentors ≤ 6.
* `public_mentor`: only verified, active mentors (404 otherwise; admins may view unverified mentors so they can verify them).
* `student_card`: mentors only for students who sent them a request (D-14).
* Masking: contact details appear only after acceptance (US-02 acceptance criterion 2, US-08 acceptance criterion 1).

## C3 Tags ✅
**Files:** `routes/tags.py`, `services/tag_service.py` (ported from FastAPI `services/tag_service.py`).
`list_tags` (approved only, public), `suggest` (saved unapproved, case-insensitive duplicate check, admins notified), `admin_create`, `admin_update` (approve / reject-and-delete if unused / rename).

## C4 Mentor Directory ✅ (US-05)
**Files:** `routes/mentors.py`, `services/directory_service.py` (ported from FastAPI `services/mentor_directory_service.py`).
Lists verified, active mentors. Free slots are computed from active mentorships, not stored. Filters: `q`, `industry`, `area`, `expertise`, `has_slots`. Sorts: best match (shared tags), free places, experience. Paginated. Each item has `can_request` (false if paused or full, or the student already has a mentor).
*Note:* filtering after the base SQL query happens in Python, which is fine for a programme-sized mentor list. Move it into SQL if there are thousands of mentors.

## C5 Requests ✅ (US-06, US-07, US-08, US-09 expiry)
**Files:** `routes/requests.py`, `services/request_service.py` (ported from FastAPI `services/request_service.py`).
* `move(req, to, actor)`: the **only** place a status changes. It always writes a `request_status_history` row (actor NULL = System). This is M2's "History writer".
* `create`: lazy expiry → role check (students for themselves; coordinator/admin must give `student_id`) → `lock_mentor` → paused? full? student already matched? 3 pending? duplicate? → insert request + history + notification → commit.
* `list_for` / `get_for`: students see their own, mentors their inbox, staff everything but without messages. Anything else → 404.
* `withdraw`: own pending only; notifies the mentor.
* `decide`: own inbox only; pending only (decided = final). Reject: optional reason. Accept: lock, re-check verification, capacity and the student's mentorship (409), create the mentorship, close the student's other pending requests (System), notify. All in one transaction.
* `expire_due_requests`: pending past `expires_on` → expired (System), both notified. Called before every request operation and by `flask run-jobs`.

## C6 Mentoring ✅
**Files:** `routes/misc.py` (mentoring section), `services/mentoring_service.py` (ported from FastAPI Development `services/mentoring_service.py`).
`list_for`, `request_end` (mutual end ends immediately; otherwise the other side is told it ends in 15 days), `cancel_end`, `end_mentorship` (cancels future sessions, notifies), `auto_end_due` (the 15-day rule, run by `run-jobs`). Mentorships are only created by C5's accept, and lowering capacity never ends one.

## C7 Goals ⏳ · C8 Availability ⏳ · C9 Sessions ⏳ · C10 Action Items ⏳ · C11 Feedback ⏳ · C12 Reports ⏳
**Tables exist** (`models/activities.py`, with the D-22 fixes). The frontend pages work **in the browser only** for now (localStorage).
FastAPI references: Goals on branch `origin/goals`; Sessions on `origin/feature/session-management` (`services/session_service.py`). Port them the same way as C5: service + repository queries + route + tests.

## C13 Notifications ✅ (US-13)
**Files:** `services/notification_service.py`, routes in `routes/misc.py`.
`notify(uid, message, link, rid)` only *adds* to the caller's transaction (M2: "components call notify inside their transaction"). `list_for`, `mark_read` (404 for other users' notifications), `mark_all_read`.

## C14 Account Lifecycle 🟡
**Done:** `services/admin_service.py`: admin user list and mentor verification (needed for Sprint 1, D-17). Blocked statuses are refused at login (403) and on every API call (401).
**Sprint 2:** deletion request with confirmation and consequences, deactivate/blacklist cascade (close pending requests as `closed_by_admin`, end mentorships with Admin_Action, notify), 30-day anonymisation.

## C15 Insights and Matching ⏳
Coordinator/admin screens currently compute their figures in the browser from the data the API returns to staff (requests without messages, mentorships, users for admin). The aggregate endpoints `/insights/*` and `/matching/candidates` are Sprint 2. Coordinator assignment through `POST /api/requests` with `student_id` already works in the API (D-24).

## C16 Scheduler 🟡
**Files:** `services/jobs.py`, CLI `flask --app app run-jobs`.
**Done:** request expiry (also lazy) and the mentorship 15-day auto-end. **Sprint 2:** stuck-request reminders (`request.reminded_on` column ready), completing sessions after their end time, purging accounts.
Why no background thread: Flask's debug reloader starts the app twice, which would run every job twice (D-16). For production, schedule `run-jobs` with cron or Windows Task Scheduler.
