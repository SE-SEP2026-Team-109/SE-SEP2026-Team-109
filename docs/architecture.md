# Architecture

## 1. The big picture

MentorConnect is three parts that talk in one direction:

```
 Browser                         Flask backend (Python)                      Database
┌───────────────────┐  HTTP+JSON ┌──────────────────────────────────────┐   ┌──────────────┐
│ Vue 3 app (Vite)  │ ─────────► │ routes  →  services  →  repositories │──►│ SQLite file  │
│ pages, components │  /api/...  │ (HTTP)    (rules)      (queries)     │   │ instance/    │
│ useStore (cache)  │ ◄───────── │        ↘ models (tables) ↙           │◄──│ mentorconnect│
└───────────────────┘   JWT      └──────────────────────────────────────┘   │ .db          │
                                                                             └──────────────┘
```

* The **frontend** shows pages and collects input. It does not decide business rules any more.
  It asks the backend and shows the backend's answer, or its error message.
* The **backend** enforces every rule (limits, permissions, privacy) and is the only part that
  touches the database. A rule enforced only in the browser is not a rule: anyone can call the API directly.
* The **database** (SQLite for development, PostgreSQL-compatible) stores the data permanently.

In development, Vite serves the frontend on `http://localhost:5173` and forwards every `/api/...`
call to Flask on `http://127.0.0.1:5000` (see `frontend/vite.config.js`). The browser therefore talks
to one address, and there are no CORS problems.

## 2. Backend layers (Milestone 2 "modular monolith")

| Layer | Folder / file | Does | Must not |
|---|---|---|---|
| Route (blueprint) | `backend/app/routes/*.py` | Read the HTTP request, validate its *shape* (Pydantic schema), call **one** service function, return a DTO and status code. | Contain business rules or SQL. |
| Schema | `backend/app/schemas.py` | Describe valid request bodies (types, lengths, ranges). | Touch the database. |
| Service | `backend/app/services/*_service.py` | Business rules, permission decisions, transactions (commit/rollback), notifications, status history. | Know about HTTP (it raises `AppError`s, not responses). |
| Repository | `backend/app/repositories.py` | The reusable queries (count pending requests, active mentorships, …). | Commit or decide anything. |
| Model | `backend/app/models/*.py` | Tables, columns, relationships, constraints, enums. | Hold business rules. |
| DTO | `backend/app/services/dto.py` | Turn models into JSON. **Privacy masking happens here**, so the password hash can never leak. | – |
| Cross-cutting | `security.py`, `errors.py`, `config.py` | JWT guard, role guard, error JSON format, all limits in one place. | – |

Why so many layers? Each rule lives in exactly one place. For example, "3 pending requests"
is the single constant `MAX_PENDING_REQUESTS` in `config.py`, used by `request_service.create`.

### Request walk-through: a student sends a request

1. `MentoringRequestPage.vue` calls `submitRequest()` in `useStore.js`.
2. `useStore` calls `apiCreateRequest()` in `api.js`, which sends `POST /api/requests` with the JWT.
3. `routes/requests.py` → `@login_required` checks the token and loads the user, then `parse_body(RequestCreate)` checks the 50–1500 rule.
4. `request_service.create()` locks the mentor row, checks pause, capacity, the one-mentor rule, the 3-pending limit and duplicates. It then inserts the request, its first history row and the mentor's notification, and commits once (all or nothing).
5. The route returns the Request DTO (`201`). `useStore` reloads the request list, and the page shows "Request sent".
6. If any rule fails, the service raises `Conflict("…")`. `errors.py` turns it into `409 {"error": {...}}`, and the page shows the message.

## 3. Authentication and authorisation

```
login form ──POST /api/auth/login {email,password}──► auth_service.login
                                                      ├─ bcrypt.checkpw(password, stored hash)
                                                      ├─ status must be active (else 403)
                                                      └─ JWT {sub: user id, role, exp: +120 min} signed with SECRET_KEY
browser keeps token in localStorage ("mentorconnect_token")
every API call ──Authorization: Bearer <token>──► @login_required / @roles_required(...)
                                                      ├─ invalid/expired → 401 → frontend signs out, shows "session expired"
                                                      ├─ wrong role → 403
                                                      └─ g.current_user = the user
services then apply record-level rules ("participant guard"): not yours → 404
```

* **Passwords** are stored only as bcrypt hashes (`security.hash_password`).
* **Roles:** students and mentors self-register; coordinator and admin accounts are seeded (M2 C1).
* **Three levels of protection:** (1) a valid token, (2) the right role for the endpoint, (3) being a participant in the record (or 404).
* **Privacy masking** (`dto.can_see_contact`): email and phone are shown only to the user, admins, and an accepted student–mentor pair. Admins and coordinators never receive request message text.
* The frontend route guard (`router/index.js`) only decides which pages to show. It is a convenience, not security.

## 4. Database

Tables (SQLAlchemy models in `backend/app/models/`). ✱ = new compared to the FastAPI/DBML schema (see decisions.md).

| Component | Table | Key columns / relationships |
|---|---|---|
| C1/C2 | `users` | id, username (unique), name, `urole`, email (unique), password (hash), phone, photo, status, delete_time |
| C2 | `student` | id → users.id (1-to-1), course, courselevel, type, careergoal, rollno, mneeds, ✱skills (JSON) |
| C2 | `mentor` | id → users.id (1-to-1), designation, company, experience, capacity (check 0–10), veri_status, pause, ✱industry, ✱career_area, ✱support_types, ✱linkedin |
| C3 | `tag`, `user_tags` | tag (name+type unique, t_status = approved); user_tags (uid, tag_id) composite key |
| C5 | `request` | sid → student, mid → mentor, status, student_message, mentor_response, req_source, assigned_by → users, ✱expires_on, ✱reminded_on; indexes (sid,status), (mid,status) |
| C5 | ✱`request_status_history` | rid → request, from_status, to_status, actor_id → users (NULL = System), actor_role, changed_on |
| C6 | `mentorship` | rid → request (unique: one mentorship per accepted request), start, end, student/mentor_end_requested_at, status |
| C13 | `Notifications` | uid → users, message, ✱link, marked_on (read time), rid → request, session_id → session |
| C7 | `trackgoal` | sid → student, mgid → mentorship, title, status (✱todo added), deadline, visibility, ✱tags |
| C8 | `availability` | mid → mentor, start_time, end_time, status |
| C9 | `session` | mgid → mentorship, available_id → availability (unique, ✱nullable), ✱start_time/end_time, status, notes |
| C10 | `session_action_items` | session_id → session, assigned_to → users, ✱created_by, item, status |
| C11 | `feedback`, `platform_feedback` | feedback: mgid, ✱giver_id, ✱receiver_id, session_id (✱nullable), ✱kind, ratings, ✱is_public; platform_feedback has no user id (anonymous) |
| C12 | `report_user` | reporter → users, ✱reported_user → users, mgid (✱nullable), category, status, actions, attachment |

Sprint 2 tables (C7–C12) exist now but have no API yet.

```
users 1─1 student            users 1─1 mentor            users 1─* user_tags *─1 tag
student 1─* request *─1 mentor      request 1─* request_status_history
request 1─0..1 mentorship    mentorship 1─* session, trackgoal, feedback, report_user
users 1─* Notifications      mentor 1─* availability 1─0..1 session 1─* session_action_items
```

## 5. Frontend structure

See [frontend-integration.md](frontend-integration.md). In short: pages call functions in
`src/composables/useStore.js`. Those call `src/api.js`, and server JSON is translated by
`src/composables/adapters.js` into the shapes the pages already used. The visual design,
routes and page structure are unchanged.

## 6. Folder layout

```
repo-team109/
├── README.md                 project overview + quick start
├── backend/                  Flask application (this work)
│   ├── app/__init__.py       create_app(): config, DB, CORS, blueprints, CLI
│   ├── app/config.py         settings + every business limit
│   ├── app/models/           tables
│   ├── app/schemas.py        request validation
│   ├── app/repositories.py   shared queries
│   ├── app/services/         business rules (one file per component) + dto.py + jobs.py
│   ├── app/routes/           blueprints (auth, profile, tags, mentors, requests, misc)
│   ├── app/seed.py           demo data
│   ├── tests/                pytest suite
│   ├── run.py                python run.py → http://127.0.0.1:5000
│   └── requirements*.txt
├── frontend/                 existing Vue 3 app (connected to the API)
├── legacy/fastapi_backend/   teammates' FastAPI implementation (reference only, not run)
└── docs/                     this documentation
```
