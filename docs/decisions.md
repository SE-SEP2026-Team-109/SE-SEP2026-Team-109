# Decisions and open questions

This file records every place where the implementation had to choose between conflicting
sources, or where the milestone documents were silent. Source-of-truth order used:
**Milestone 1 acceptance criteria → Milestone 2 design and minutes → existing frontend → FastAPI code → engineering judgement.**

Status key: ✅ decided (with the reason) · ❓ open: needs a team decision.

## Project-level decisions

| ID | Decision | Why |
|---|---|---|
| P-01 ✅ | The backend is **Flask** (not FastAPI). FastAPI code is kept in `legacy/fastapi_backend/` as reference. | M1 §5.1 and M2 §1 commit to Flask + SQLAlchemy + PyJWT. Team decision (Nov 2026). The FastAPI code was moved with `git mv`, so its history and authorship are preserved; the `Development` branch is untouched. |
| P-02 ✅ | Work happens on branch `feature/flask-backend-integration`, created from `origin/Development`. | Never modify `Development` directly. |
| P-03 ✅ | The new branch's frontend = `Development`'s frontend (with Abhinava's first API wiring: `api.js`, register/login/profile) **plus** the UI-only changes from `feature/update-frontend` (theme v3 block, "User feedback" nav label, AccountPage layout). | The two branches had diverged; each had work the other lacked. Only `theme.css`, `AppLayout.vue` and `AccountPage.vue` were taken from `feature/update-frontend`, because their differences were purely visual. |
| P-04 ✅ | No migration tool (Flask-Migrate) yet. Tables are created by `db.create_all()` (creates missing tables only, never drops) and `flask --app app init-db`. `flask --app app reset-db --yes` wipes and re-seeds, and refuses without `--yes`. | Simpler for a beginner team. **Limitation:** adding a column to an existing table needs a reset (or a migration tool later). All Sprint 2 tables were created now, so Sprint 2 should not need a reset. |
| P-05 ✅ | The browser mock mode was removed for the Sprint 1 features. Sprint 2 features (goals, sessions, availability, feedback, reports, coordinator groups and to-dos) still run **in the browser only**, saved in `localStorage` key `mentorconnect_local_v1`. | Preserves every existing frontend feature (none were removed) while being honest that they are not yet backed by the database. Each will move to the API in Sprint 2. |
| P-06 ✅ | The demo data (`backend/app/seed.py`) mirrors the old `mock.js`: same people, same emails, password `Demo1234`. | The login page's demo buttons and the team's demo script keep working. The demo student emails (e.g. `student@mentorconnect.demo`) do not end in `study.iitm.ac.in`; they are inserted directly, as the mock did. The domain rule applies to everyone who registers. |

## Rule and schema decisions

| ID | Topic | Conflict | Decision |
|---|---|---|---|
| D-01 ✅ | Reject reason | M1 US-08 says "optional"; FastAPI required it. | **Optional** (M1 wins; confirmed by the team). Max 500 characters. |
| D-02 ✅ | Mentor capacity range | M1 US-04 "Specific" says 0–10; its acceptance criteria and US-03 say 1–10; FastAPI allowed 0–10. | **1–10** in the API (acceptance criteria are the testable source). The DB check constraint still allows 0 so that a future "0 = closed" option needs no migration. Use **Pause** to stop new requests. |
| D-03 ✅ | Pause toggle | US-04 requires it; FastAPI's profile update did not allow changing `pause`. | `PUT /api/profile/me` accepts `mentor.pause`. |
| D-04 ✅ | Request expiry storage | M2 C5 says `expires_on = created + 14 days`; FastAPI calculated it on the fly. | New column `request.expires_on`. |
| D-05 ❓ | "Between jobs" employment | The UI offers "Studying only" and "Between jobs"; the DB enum has only `standalone` for both. | Both are saved as `standalone`, which is shown as "Studying only". **Team:** add a `between_jobs` enum value if the difference matters. |
| D-06 ❓ | Coordinator to-do list, coordinator groups, relay messages, admin audit log | Present in the frontend; no table in the M2 design. | Kept as browser-only features (not removed). **Team:** add tables in Sprint 2, or drop them from the UI. |
| D-07 ❓ | Admin "merge duplicate tags" | In the frontend; no API in M2. | The button now explains that merging is not connected yet. Admins can edit or reject a duplicate instead. **Team:** add `POST /api/admin/tags/{id}/merge` in Sprint 2? |
| D-08 ✅ | Request status history | M1 §4.4 and M2 "History writer" require it; FastAPI had no table. | New table `request_status_history` (`from_status`, `to_status`, `actor_id`, `actor_role`, `changed_on`). NULL actor = System. Written by one function (`request_service.move`) so no change can skip it. |
| D-09 ✅ | Industry / career area / support types | US-03 requires support types; US-05 searches by industry and career area. The DBML had no columns; FastAPI used tag types instead. | New mentor columns `industry`, `career_area`, `support_types` (JSON list), `linkedin`. The directory filters match these columns **and** domain/expertise tags. |
| D-10 ✅ | Student free-text skills | The profile page collects skills with level 1–5 and "want to learn". `user_tags` only accepts admin-approved tags. | `student.skills` JSON column. Interests stay in `user_tags` (approved tags, max 5) as M2 C3 requires. |
| D-11 ✅ | Profile photo | M2 C2 plans `POST /profile/me/photo` (upload). FastAPI stored a URL in `String(255)`. The frontend resizes the photo to a 200 px data URL. | `users.photo` is `Text` and accepts `https://` or `data:image/` URLs up to 400 KB. A real upload endpoint is Sprint 2 (C2/C12 "File storage"). |
| D-12 ✅ | Who can see email/phone | US-02/US-08: hidden until accepted. Silent for staff. | Visible to the user themself, to admins, and to a student/mentor pair after **acceptance**. Coordinators see no contact details (their screens are anonymised in the frontend). |
| D-13 ✅ | Admins/coordinators reading requests | M2 Meeting 5: staff must not read request messages. | `GET /api/requests` works for staff but `student_message` and `mentor_response` are `null` for them. |
| D-14 ✅ | Student card for mentors | FastAPI let any mentor open any student card. M2: "card for a mentor reviewing a request". | A mentor gets 404 unless that student has sent them a request. |
| D-15 ✅ | Capacity race (M1 edge case 1) | SQLite ignores `SELECT … FOR UPDATE` (FastAPI's lock did nothing; two locks were commented out). | `repositories.lock_mentor` issues a no-op `UPDATE` on the mentor row first. SQLite then takes its write lock, so a second accept waits and its re-check returns **409**. PostgreSQL uses `FOR UPDATE`. |
| D-16 ✅ | Scheduler (C16) | M2 lists daily/hourly jobs. | Request expiry runs **lazily** before every request operation (so it is always correct) and via `flask --app app run-jobs`. The 15-day mentorship auto-end is in `run-jobs`. No background thread runs inside Flask: the debug reloader would run each job twice. Reminders, session completion and account purge: Sprint 2. |
| D-17 ✅ | Mentor verification endpoint | M2 says "mentor hidden from search until verified" but lists no endpoint. | `PATCH /api/admin/mentors/{id}/verification` with `{"status": "verified" \| "rejected" \| "pending"}`. Needed for the Sprint 1 register → verify → visible flow. |
| D-18 ✅ | Admin tag routes | M2 says `/admin/tags`; FastAPI used `/tags/admin`. | M2's `/api/admin/tags` (plus `GET` for the admin list including pending suggestions). |
| D-19 ✅ | Extra small endpoints | Not in M2 but needed by existing UI. | `POST /api/auth/change-password`, `POST /api/auth/logout` (client discards the JWT), `PATCH /api/notifications/read-all`, `GET /api/admin/users`. |
| D-20 ✅ | Login body | FastAPI used OAuth2 form fields (`username`, `password`). | JSON `{"email","password"}`. Form fields are still accepted so an old client keeps working. |
| D-21 ✅ | JWT subject | FastAPI put the email in `sub`. | User **id** in `sub` (email can change or be anonymised by account deletion). |
| D-22 ✅ | Feedback, report, session schema (Sprint 2 tables) | Frontend lets mentors give feedback and has "final" feedback; reports can target someone outside a mentorship (M2 Meeting 8); logged past sessions have no slot. | `feedback.giver_id/receiver_id/kind/is_public` (session optional); `report_user.mgid` nullable + `reported_user`; `session.available_id` nullable (still unique) + `start_time/end_time`; `trackgoal` default status `todo` (as on the team's FastAPI `goals` branch). |
| D-23 ❓ | Re-requesting the same mentor after rejection/expiry | M2 open point (§8.2). | Allowed now (only a second **pending** request to the same mentor is blocked). **Team:** add a cool-down? |
| D-24 ❓ | Coordinator matching | The frontend creates a mentorship directly. M2 C5 says coordinator-assigned requests "still need mentor acceptance". | The API implements M2 (`POST /api/requests` with `student_id` creates a pending request). The coordinator Matching screen is still browser-only until C15 provides the student list (Sprint 2). |

## FastAPI teammate work that is still unique

* `origin/goals` (Nov 20–21): Goals APIs (C7). Use it as the reference when porting C7 to Flask.
* `origin/feature/session-management`: Sessions APIs (C9). Not merged into Development; it conflicts with Development on `main.py` and `models/mentoring.py`. Reference for C9.
