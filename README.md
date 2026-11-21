<div align="center">

# 🧭 MentorConnect

**Guidance that moves you forward.**
A mentoring platform that connects IITM BS students with alumni who have been where they are headed.


</div>

---

## 💡 Why it exists

Students nearing graduation face big career choices and often have no one to ask. Mentors are willing but get flooded. MentorConnect fixes both sides:

| Students said | Mentors said | So the platform |
|---|---|---|
| "I stare at LinkedIn profiles for an hour but never send a message." | "I got 15 emails in one week, so I stopped replying." | gives a searchable directory, a guided request, and **hard capacity limits** |
| "My request just disappeared." | "I felt guilty about ghosting." | shows request status and **expires unanswered requests after 14 days** |
| "We talked, then nothing happened." | "Students don't follow the advice." | tracks **goals, sessions and action items** |

## 🚀 Quick start

You need **Python 3.10+** and **Node.js 18+**. Open two terminals.

**1. Backend (Flask API)**
```bash
cd backend
python -m venv venv
venv\Scripts\activate                 # macOS/Linux: source venv/bin/activate
pip install -r requirements-dev.txt
copy .env.example .env                # macOS/Linux: cp .env.example .env  (then set SECRET_KEY)
python run.py                         # http://127.0.0.1:5000/api/health
```

**2. Frontend (Vue 3)**
```bash
cd frontend
npm install
npm run dev                           # http://localhost:5173  (calls to /api are proxied to Flask)
```

Demo data is created on first start in `backend/instance/mentorconnect.db`.
To reset it: `flask --app app reset-db --yes` (inside `backend`, venv active). **This deletes all data.**

## 🎬 Try it in 3 minutes

All demo passwords are `Demo1234`. The login page also has a one-click demo student button.

| Step | Sign in as | Do this |
|---|---|---|
| 1 | `student@mentorconnect.demo` (student) | Open **Mentors**, filter by career area, send a request to Neha Kulkarni (50+ characters) |
| 2 | `neha.kulkarni@alumni.demo` (mentor) | Open **Requests**, accept it: the student's email appears and capacity updates |
| 3 | `student@mentorconnect.demo` | **Requests**: Neha accepted, the pending request to Priya was closed by **System**; check **Alerts** |
| 4 | `admin@mentorconnect.demo` (admin) | **Users**: verify a newly registered mentor; **Content**: approve a suggested tag |

Mentors who register themselves stay hidden from students until an admin verifies them. Students must register with an address ending in `study.iitm.ac.in`.

## ✨ What it does

<table>
<tr><td width="50%" valign="top">

### 🎓 For students
- Build a profile with level, interests, needs and up to 5 expertise areas
- Search mentors by career area, with an "open places" filter
- Send up to 3 pending requests at a time
- Withdraw a request any time, or let it expire after 14 days
- Track goals, book mentor slots, log sessions, message mentors
- Report a user, or delete the account

</td><td width="50%" valign="top">

### 🤝 For mentors
- Publish a profile with company, experience and support types
- Set capacity (1 to 10) and pause new requests
- Accept or decline with an optional reason
- Offer availability slots with no overlaps and no past times
- Read mentees' goals, log sessions, give private feedback

</td></tr>
<tr><td valign="top">

### 🧩 For coordinators
- See where student demand outruns mentor places
- Match unmatched students, who stay anonymous until matched
- Remind mentors about stuck requests

</td><td valign="top">

### 🛡️ For administrators
- Participation, acceptance rate and effectiveness insights
- Verify mentors, deactivate accounts
- Review reports and record the action taken

</td></tr>
</table>

### Rules the system enforces

- A full or paused mentor cannot receive requests. Lowering capacity never ends a current mentorship.
- Accepting a request unmasks both emails. A decided request cannot go back to pending.
- Anyone who is not part of a record gets a 404, so IDs cannot be probed.
- Mentors see goals but cannot edit them. Session dates cannot be in the future.
- Every status change is logged with who did it (`System` for expiry).
- Account deletion shows its effects first, then anonymises data after 30 days.

> **Build status (Sprint 1 / Milestone 3):** everything for US-01 to US-08 runs on the Flask API and
> database and is tested. Goals, availability, sessions, action items, feedback, reports, account
> deletion and coordinator matching still work **in the browser only** (data kept in localStorage)
> until their Sprint 2 APIs are built. See [docs/traceability.md](docs/traceability.md).


## 🏗 How it fits together

```mermaid
flowchart LR
    S[Student] & M[Mentor] & C[Coordinator] & A[Admin] --> UI[Vue 3 app]
    UI -- "/api + JWT" --> R[Flask blueprints]
    R --> SV[Services: rules, transactions]
    SV --> RP[Repositories / SQLAlchemy models]
    RP --> DB[(SQLite)]
    SV --> N[In-app notifications]
    SV --> H[Request status history]
```

<details>
<summary><b>Request lifecycle</b></summary>

```mermaid
stateDiagram-v2
    [*] --> pending
    pending --> accepted: mentor accepts
    pending --> rejected: mentor declines (optional reason)
    pending --> withdrawn: student withdraws / System when matched elsewhere
    pending --> expired: 14 days pass (System)
    pending --> closed_by_admin: admin blocks a user (Sprint 2)
```
</details>

<details>
<summary><b>Tech stack and folders</b></summary>

| Area | Technology |
|---|---|
| Backend | Python, Flask 3, Flask-SQLAlchemy (SQLAlchemy 2), Pydantic validation, PyJWT, bcrypt |
| Database | SQLite (PostgreSQL-compatible models) |
| Auth | JWT, 120-minute expiry, role and participant guards |
| Frontend | Vue 3, Vue Router, Vite |
| Tests | pytest (53 backend tests) |

```
backend/   Flask app: app/ (models, schemas, repositories, services, routes), tests/, run.py
frontend/  Vue app: src/api.js (API client), src/composables/ (store + adapters), src/pages/
docs/      architecture, API reference, components, frontend integration, testing, traceability, decisions, handover
legacy/fastapi_backend/  earlier FastAPI implementation by the team (reference only)
```
</details>

## 🧪 Tests

```bash
cd backend
venv\Scripts\python -m pytest          # macOS/Linux: venv/bin/python -m pytest
```

53 tests cover sign-up rules, login and tokens, roles, profiles, tags, the directory, request limits,
capacity, expiry, accept/reject/withdraw, mentorship ending, notifications and privacy (404 for others' records).
Results and the end-to-end browser test: [docs/testing.md](docs/testing.md).


## 📚 Project docs

| Document | Contents |
|---|---|
| [docs/handover.md](docs/handover.md) | Start here: beginner guide, install, demo script, how to continue |
| [docs/architecture.md](docs/architecture.md) | System, layers, auth flow, database tables |
| [docs/backend-components.md](docs/backend-components.md) | C1–C16: files, functions, rules, status |
| [docs/api-reference.md](docs/api-reference.md) | Every endpoint: method, roles, body, response, errors |
| [docs/frontend-integration.md](docs/frontend-integration.md) | Page → API map, how mock data was replaced, JWT in the browser |
| [docs/testing.md](docs/testing.md) | Test cases, results, bugs fixed, what is untested |
| [docs/traceability.md](docs/traceability.md) | User stories and acceptance criteria → components → code → tests |
| [docs/decisions.md](docs/decisions.md) | Deviations, conflicts resolved, open questions |

<details>
<summary><b>User stories (16)</b></summary>

| ID | Story | Sprint |
|---|---|---|
| US-01 | Register and sign in with role-based access | 1 |
| US-02 | Create a student mentoring profile | 1 |
| US-03 | Create a mentor profile | 1 |
| US-04 | Manage mentoring capacity | 1 |
| US-05 | Search for mentors | 1 |
| US-06 | Submit a mentoring request | 1 |
| US-07 | Track request status | 1 |
| US-08 | Review and decide on requests | 1 |
| US-09 | Automated request expiry | 2 |
| US-10 | Define and track career goals | 2 |
| US-11 | Monitor platform participation | 2 |
| US-12 | Session feedback and action items | 2 |
| US-13 | Receive notifications | 2 |
| US-14 | Request account deletion | 2 |
| US-15 | Report inappropriate behaviour | 2 |
| US-16 | Manage mentor availability | 2 |
</details>

<details>
<summary><b>Schedule, milestones and tracking</b></summary>

| Milestone | Focus | Deadline |
|---|---|---|
| 1 | User requirements | Oct 25, 2026 |
| 2 | Scheduling and design | Nov 07, 2026 |
| 3 (Sprint 1) | APIs, tests, user testing (US-01 to US-08) | Nov 22, 2026 |
| 4 (Sprint 2) | APIs, tests, user testing (US-09 to US-16) | Dec 06, 2026 |
| 5 | Final report and prototype | Dec 20, 2026 |

Keep your exported diagrams in `docs/`: `gantt-chart.png`, `kanban-board.png`, `er-diagram.png`, `class-diagram.png`.

Scrum schedule and minutes go in `docs/scrum-minutes.md`. Issues, pull requests and code review screenshots go in `docs/`.
</details>

## 👥 Team

**Team 109 · IITM BS Software Engineering · September 2026 term · Option 2**

| Name | Roll number |
|---|---|
| Amit Kumar Gupta | 24F1002112 |
| Ovya Anand | 22f3001028 |
| Abhinava Maharudrappa Alur | 21F2000353 |
| Amol Wani | 21F1005443 |
| Taruna Choudhary | 22F3002199 |
| Amruthavarshini M | 21F3001976 |
