# Team handover: MentorConnect backend (beginner-friendly)

## 1. What MentorConnect is, in one paragraph
MentorConnect helps IITM BS students find alumni mentors without cold-messaging on LinkedIn.
Students build a profile, search a directory of verified mentors, and send a short request.
Mentors set a hard capacity, so they are never flooded, and accept or decline. Unanswered requests
expire after 14 days, so nobody waits forever. Coordinators and admins watch the health of the programme.

## 2. What changed in this branch, and why

| Before | After (`feature/flask-backend-integration`) |
|---|---|
| The Vue frontend kept all data in the browser (mock data, `localStorage`); rules ran in the browser; passwords stored in plain text | A **Flask** backend with a **SQLite** database stores the data. All Sprint 1 rules run on the server; passwords are bcrypt-hashed; access uses **JWT** tokens |
| Teammates built a FastAPI backend (auth, profile, tags, directory, requests, mentoring) on branches; M1/M2 promised Flask | The FastAPI business logic was **ported** to Flask (same rules, plus what M1/M2 required and FastAPI lacked). FastAPI code is preserved in `legacy/fastapi_backend/` |
| Two frontend versions had diverged | Merged: Development's frontend + the UI updates from `feature/update-frontend` |

**Sprint 1 (US-01 to US-08) is fully connected end to end and tested.** Sprint 2 pages still work
but keep their data in the browser until their APIs are built (see traceability.md).

## 3. Key technical decisions (the short version)
1. **Flask, because the milestone documents committed to it.** FastAPI became the reference for business rules.
2. **Three backend layers:** routes (HTTP) → services (rules) → repositories/models (database). Each rule lives in one place.
3. **The server is the authority.** The browser shows the server's answer; hiding a button is never security.
4. **Privacy by default:** emails hidden until a request is accepted; admins and coordinators never see request messages; other people's records return 404.
5. **Status history for every request change**, with "System" for automatic changes (expiry, auto-close).
6. **The pages did not change visually.** A translation file (`adapters.js`) makes server data look like the old mock data.
7. Full list with reasons: [decisions.md](decisions.md). Open questions for the team are marked ❓ there.

## 4. Install and run (Windows; macOS/Linux commands in brackets)

You need **Python 3.10+** and **Node.js 18+**. Use two terminals.

**Terminal 1: backend**
```powershell
cd backend
python -m venv venv
venv\Scripts\activate                 # [source venv/bin/activate]
pip install -r requirements-dev.txt
copy .env.example .env                # [cp .env.example .env]  then put a long random SECRET_KEY in .env
python run.py                         # API on http://127.0.0.1:5000  (try http://127.0.0.1:5000/api/health)
```
The first start creates `backend/instance/mentorconnect.db` and fills it with demo data.

**Terminal 2: frontend**
```powershell
cd frontend
npm install
npm run dev                           # open http://localhost:5173
```

**Demo accounts** (password `Demo1234` for all):

| Role | Email |
|---|---|
| Student | `student@mentorconnect.demo` (Aarav) · also `meera.iyer@ds.study.iitm.ac.in`, `sneha.patil@ds.study.iitm.ac.in`, … |
| Mentor | `mentor@mentorconnect.demo` (Priya) · `neha.kulkarni@alumni.demo`, `rahul.menon@alumni.demo`, … |
| Coordinator | `coordinator@mentorconnect.demo` |
| Admin | `admin@mentorconnect.demo` |

**Useful commands** (run inside `backend` with the venv active):
```powershell
python -m pytest                      # run all backend tests
flask --app app run-jobs              # run scheduled jobs once (expire requests, auto-end mentorships)
flask --app app reset-db --yes        # DELETE ALL DATA and recreate the demo database
```

## 5. A 3-minute demo script
1. Sign in with the **demo student** button → **Mentors**: places free, paused and full mentors come from the database.
2. Request **Neha Kulkarni** (write 50+ characters) → **Requests**: pending, "Expires in 14 days". Dr. Seth's old request shows **Expired by System**.
3. Sign out → sign in as `neha.kulkarni@alumni.demo` → **Requests** → open it: the student's email is hidden → **Accept**: the email appears, capacity 1 of 3, history shows *Accepted by Mentor*.
4. Back as the student: the request to Priya was **closed by System** automatically (one-mentor rule), and a notification arrived.
5. Register a new mentor → sign in as **admin** → Users → **Verify** → the mentor now appears in the student directory.
6. Show `pytest`: 53 tests passing.

## 6. How to explain the backend to the team (talking points)
* "The frontend asks and the backend decides. Every rule from Milestone 1 (3 pending requests, 50–1500 characters, capacity, 14-day expiry, email masking) is checked in a **service** on the server and tested with pytest."
* "A request goes **route → service → repository → database**. The route only checks the shape of the input. The service applies the rules and saves everything in **one transaction**, so it is all or nothing."
* "We log in with **JWT**: the server signs a token containing our user id and role. The browser sends it with every call. After 120 minutes it expires and the app signs us out."
* "Privacy: if a record is not yours, the API says **404 Not Found**, not 403, so nobody can guess ids (M1 §4.2)."
* "Every status change writes a **history row**, with 'System' when the change was automatic."
* "We reused our FastAPI work: the Flask services are ports of `request_service.py`, `mentoring_service.py`, `tag_service.py` and others, with the missing M1 rules added."

## 7. How to continue (Sprint 2 recipe)
To add a component (for example C7 Goals):
1. The **table** already exists in `backend/app/models/activities.py`.
2. Add request schemas to `app/schemas.py` (copy the field rules from FastAPI branch `origin/goals`, `schemas/goals.py`).
3. Create `app/services/goal_service.py`: rules, permission checks (404 for non-owners), `db.session.commit()`, `notify(...)` where M2 says so.
4. Add queries you reuse to `app/repositories.py`.
5. Create `app/routes/goals.py` with a `Blueprint`, and register it in `app/__init__.py`.
6. Write tests in `backend/tests/test_goals.py` (copy the style of `test_requests_mentoring.py`).
7. Frontend: add `apiGoals…` functions to `src/api.js`, add a `toGoal` adapter, and make the functions in `useStore.js` call them (`async` + `await`, then reload). Remove `'goals'` from `LOCAL_SLICES`.
8. Update `docs/api-reference.md`, `docs/traceability.md` and `docs/testing.md`.

Priority order suggested for Sprint 2: C7 Goals → C8 Availability → C9 Sessions → C10 Action items → C11 Feedback → C12 Reports → C14 lifecycle → C15 insights → C16 remaining jobs.

## 8. Things to know / gotchas
* **No migrations yet:** if you add a column to an existing table, run `flask --app app reset-db --yes` (demo data comes back) or introduce Flask-Migrate.
* The SQLite file is in `backend/instance/` and is git-ignored. Each teammate has their own.
* `legacy/fastapi_backend/` is **not run**. It is kept for reference and credit.
* The Vite dev server must run for `/api` to reach Flask (or set `VITE_API_BASE=http://127.0.0.1:5000/api`; CORS allows `localhost:5173`).
* Nothing on this branch has been committed or pushed yet. Review `git status` before committing.
