# API reference (Flask backend)

Base URL: `http://127.0.0.1:5000/api` (in development the Vue app calls `/api`, and Vite forwards it).
All bodies are JSON. Times are UTC ISO-8601 with a `Z` suffix (e.g. `2026-11-21T06:16:36Z`).

**Authentication:** send `Authorization: Bearer <access_token>` (from `/auth/login`). Tokens expire after 120 minutes.

**Error format** (every error, every endpoint):
```json
{ "error": { "status": 409, "message": "You already have 3 pending requests. Withdraw one or wait for a reply.",
             "details": [ { "field": "student_message", "message": "..." } ] },
  "detail": "same message (kept for the earlier FastAPI-style client)" }
```
| Status | Meaning |
|---|---|
| 400 | Invalid input (validation). `details` lists the fields. |
| 401 | No token, invalid token, expired token, or account no longer active. |
| 403 | Signed in, but your role may not do this. |
| 404 | Not found **or not yours**. Records you are not part of always return 404, so ids cannot be probed (M1 §4.2). |
| 409 | Business-rule conflict (limit reached, already decided, capacity full…). |
| 500 | Unexpected database error (the transaction is rolled back). |

Status column: ✅ implemented and tested · 🟡 implemented, partly tested · ⏳ Sprint 2 (not implemented). "Deviation" refers to [decisions.md](decisions.md).

---

## Common objects

**User DTO** (every response containing a user uses this; never contains the password hash)
```json
{ "id": 9, "role": "mentor", "name": "Priya Nair", "username": "priya_nair",
  "email": null, "phone": null,            // null unless you may see contact details (D-12)
  "photo": null, "status": "active", "created_at": "…Z", "delete_time": null,
  "tags": [ { "id": 1, "name": "Data Science", "type": "expertise", "want_to_learn": false, "skill_level": null } ],
  "student": null,
  "mentor": { "designation": "Senior Data Scientist", "company": "Finlytics", "experience": 7.0,
              "industry": "Fintech", "career_area": "Data Science", "support_types": ["Resume review"],
              "bio": "…", "capacity": 3, "pause": false, "veri_status": "verified",
              "iitm_program": "data_science_and_applications", "level_completed": "bsc_degree",
              "year_completed": null, "still_enrolled": null, "linkedin": null,
              "active_mentees": 1, "free_slots": 2 } }
```
For students, `student` = `{ course, courselevel (null = Foundation), type, careergoal, rollno, mneeds, skills: [{name, level, want}] }`.

**Request DTO**
```json
{ "id": 8, "sid": 5, "mid": 12, "status": "accepted",
  "created_on": "…Z", "changed_on": "…Z", "expires_on": "…Z",
  "student_message": "…",      // null for admin/coordinator (D-13)
  "mentor_response": "",       // reject reason or system note; null for admin/coordinator
  "req_source": "student", "assigned_by": null,
  "history": [ { "from": null, "to": "pending", "actor": "Student", "at": "…Z" },
               { "from": "pending", "to": "accepted", "actor": "Mentor", "at": "…Z" } ],
  "student": { …User DTO… }, "mentor": { …User DTO… } }
```

---

## C1 Auth (US-01)

| Method & path | Auth | Purpose | Status |
|---|---|---|---|
| `POST /auth/register` | none | Student or mentor self-registration. | ✅ |
| `POST /auth/login` | none | Returns a JWT and the user. | ✅ |
| `GET /auth/me` | any role | Current user. | ✅ |
| `POST /auth/change-password` | any role | `{current_password, new_password}`. Deviation D-19. | ✅ |
| `POST /auth/logout` | any role | Client deletes its token (JWT is stateless). D-19. | 🟡 |

**Register body**: common fields `email, password, role ("student"|"mentor"), name, username, phone?`.
Student extras: `course?, courselevel?, student_type?, rollno?, careergoal?, mneeds?, interests? (approved tag names, ≤5), skills? [{name, level 1-5, want}]`.
Mentor extras: `designation, company, experience, industry, career_area, bio, support_types [], expertise [] (approved tag names, ≤6), capacity (1-10, required), level_completed?, year_completed?, still_enrolled?, linkedin?`.

Rules:
* Students' email must end in `study.iitm.ac.in` (sub-domains such as `ds.study.iitm.ac.in` allowed). → 400.
* Password at least 8 characters with letters **and** digits. → 400.
* Username 3–20 lowercase letters/digits/underscore. Email and username unique. → 409.
* Coordinator/admin cannot self-register (role must be student or mentor). → 400.
* New mentors are `veri_status: "pending"` (hidden from students) and every admin is notified.

Response `201`: User DTO. **Login** response `200`:
```json
{ "access_token": "eyJ…", "token_type": "bearer", "expires_at": "…Z", "user": { …User DTO… } }
```
Errors: `401` wrong email/password (same message for both); `403` deactivated, blacklisted or scheduled for deletion.

## C2 Profile (US-02, US-03, US-04)

| Method & path | Roles | Purpose | Status |
|---|---|---|---|
| `GET /profile/me` | any | Own profile (full contact details). | ✅ |
| `PUT /profile/me` | any | Update own profile (partial). | ✅ |
| `PUT /profile/me/tags` | student, mentor | Replace tag selection: `{"names": [...]}` or `{"tags": [{tag_id, want_to_learn, skill_level}]}`. | ✅ |
| `GET /mentors/{id}` | student, coordinator, admin | Public mentor profile. Verified + active only (admins can also open unverified mentors). | ✅ |
| `GET /students/{id}/card` | mentor, coordinator, admin | Student card. A mentor needs a request from that student (D-14). | ✅ |
| `POST /profile/me/photo` | – | Photo upload. | ⏳ (D-11: photo is sent as a data URL in `PUT /profile/me`) |

`PUT /profile/me` body (all optional; unknown fields → 400):
```json
{ "username": "new_name", "name": "…", "phone": "…", "photo": "data:image/jpeg;base64,…" | "https://…" | "",
  "student": { "course": "…", "courselevel": "bs_degree", "clear_courselevel": false, "type": "…",
               "careergoal": "…", "rollno": "…", "mneeds": "…", "skills": [{ "name": "SQL", "level": 3, "want": true }] },
  "mentor":  { "designation": "…", "company": "…", "experience": 4, "industry": "…", "career_area": "…",
               "bio": "…", "support_types": ["…"], "capacity": 1-10, "pause": true, "linkedin": "…",
               "iitm_program": "…", "level_completed": "…", "year_completed": 2024, "still_enrolled": false } }
```
Sending `student` as a mentor (or `mentor` as a student) → 400. Tag limits: students ≤ 5, mentors ≤ 6, approved tags only → 400.

## C3 Tags

| Method & path | Roles | Purpose | Status |
|---|---|---|---|
| `GET /tags?type=` | **public** | Approved tags (the registration page needs them before sign-in). `type` = domain/expertise/tool/skill. | ✅ |
| `POST /tags/suggest` | any | `{"name", "type"?}` → saved as not approved; admins notified. Case-insensitive duplicate → 409. | ✅ |
| `GET /admin/tags` | admin | All tags including pending (`approved: false`). | ✅ |
| `POST /admin/tags` | admin | Create an approved tag. | ✅ |
| `PATCH /admin/tags/{id}` | admin | `{"action": "approve"\|"reject", "name"?, "type"?}`. Reject deletes a pending suggestion (409 if in use). | ✅ |

## C4 Mentor Directory (US-05)

`GET /mentors?q=&industry=&area=&expertise=&has_slots=&sort=&page=&page_size=` (roles: student, coordinator, admin) ✅

* Only active users with a **verified** mentor profile.
* `q` matches name, job title, company, bio or tag name. `industry` matches `mentor.industry` or domain tags. `area` matches `career_area` or expertise tags. `expertise` matches any tag.
* `has_slots=true` keeps mentors with free places (`free_slots = capacity − active mentorships`, 0 if paused).
* `sort`: `best_match` (default; shared tags with you, then free places), `free_slots`, `experience`. Aliases `match`, `slots`, `exp` are accepted.
* `page_size` ≤ 100.

Response: `{ "total", "page", "page_size", "total_pages", "student_has_active_mentorship", "items": [User DTO + "can_request"] }`.
`can_request` is false when the mentor is paused or full, or the student already has a mentor.

## C5 Requests (US-06, US-07, US-08, US-09)

| Method & path | Roles | Purpose | Status |
|---|---|---|---|
| `POST /requests` | student (own); coordinator/admin (with `student_id`) | Submit. | ✅ |
| `GET /requests?status=` | student (own), mentor (inbox), coordinator/admin (all, without messages) | List, newest first. | ✅ |
| `GET /requests/{id}` | participants; coordinator/admin | Detail with full status history. | ✅ |
| `POST /requests/{id}/withdraw` | the requesting student | Pending → withdrawn. | ✅ |
| `POST /requests/{id}/decision` | the receiving mentor | `{"action": "accept"\|"reject", "reason"?: "≤500 chars"}`. | ✅ |

Rules (each one is tested; see testing.md):
* Message 50–1500 characters after trimming → 400.
* Mentor must be verified and active → 404; not paused → 409; has a free place → 409.
* Student has no active mentorship → 409; fewer than 3 pending requests → 409; no other pending request to the same mentor → 409.
* `expires_on = created_on + 14 days`. Before every request operation, overdue pending requests become `expired` (actor **System**) and both sides are notified.
* Accept re-checks verification, capacity and the student's mentorship **inside the transaction** (SQLite-safe lock, D-15) → 409. Accept creates the mentorship, closes the student's other pending requests as `withdrawn` by System, and notifies everyone.
* Decided requests are final → 409. A coordinator/admin-created request has `req_source: "coordinator"` and still needs the mentor to accept.

## C6 Mentoring

| Method & path | Roles | Purpose | Status |
|---|---|---|---|
| `GET /mentoring?include_ended=` | student, mentor (own); coordinator/admin (all) | Active relationships. | ✅ |
| `POST /mentoring/{id}/end` | participants | Record your end request; ends immediately if the other side already asked (Mutual). | ✅ |
| `POST /mentoring/{id}/end/cancel` | participants | Withdraw your end request. (M2 lists GET; POST is used because it changes data.) | ✅ |

Ending cancels future sessions and notifies both. One-sided requests end automatically after 15 days (`flask --app app run-jobs`).
Mentorship DTO: `{ id, rid, sid, mid, status, start, end, student_end_requested_at, mentor_end_requested_at, assigned_by, student, mentor }`.

## C13 Notifications (US-13)

| Method & path | Roles | Purpose | Status |
|---|---|---|---|
| `GET /notifications` | any (own only) | Newest first. `{id, message, link, read, created_at, rid}`. | ✅ |
| `PATCH /notifications/{id}/read` | owner | Mark read (another user's id → 404). | ✅ |
| `PATCH /notifications/read-all` | any | Mark all own as read. D-19. | ✅ |

Generated now for: new request, withdrawal, accept, reject, auto-close, expiry, mentor registration (to admins), tag suggestion (to admins), verification, mentorship end.

## Admin (Sprint 1 part of C14)

| Method & path | Roles | Purpose | Status |
|---|---|---|---|
| `GET /admin/users` | admin | All users (full contact details). | ✅ |
| `PATCH /admin/mentors/{id}/verification` | admin | `{"status": "verified"\|"rejected"\|"pending"}`. Requires job title and company. D-17. | ✅ |
| `PATCH /admin/users/{id}/status` | admin | Deactivate/blacklist/reactivate with cascade. | ⏳ |

## Health

`GET /health` → `{"status": "ok"}` (no auth) ✅

## Sprint 2 endpoints from M2 (not implemented yet)

C7 Goals (`/goals`, `/goals/{id}`, `/goals/{id}/status`, `/students/{id}/goals`) · C8 Availability (`/availability`, `/mentors/{id}/availability`) ·
C9 Sessions (`/sessions`, `/sessions/{id}/confirm|decline|cancel|notes`) · C10 Action items (`/sessions/{id}/actions`, `/actions/{id}/status`, `/actions/{id}`) ·
C11 Feedback (`/sessions/{id}/feedback`, `/feedback/mine`, `/platform-feedback`, admin/coordinator reads) · C12 Reports (`/reports`, `/reports/mine`, `/admin/reports`) ·
C14 (`/account/deletion-request`, `/admin/users/{id}/status`) · C15 (`/insights/stats`, `/matching/candidates`, `/insights/stuck-requests`).
Their database tables already exist (see backend-components.md).
