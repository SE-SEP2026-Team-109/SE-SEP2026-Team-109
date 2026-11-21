# Frontend integration

## How the frontend used to work

Every page called functions in `src/composables/useStore.js`. Those functions changed one big
JavaScript object (`state`), which was seeded from `src/data/mock.js` and saved in `localStorage`.
Passwords were stored in plain text in the browser, and all business rules ran in the browser.
Abhinava later connected registration, login and student profile saving to the FastAPI backend
(`src/api.js`, Development branch). That work is the starting point of this integration.

## How it works now

```
Page (.vue)  ──calls──►  useStore.js function  ──calls──►  api.js request()  ──HTTP──►  Flask
   ▲                            │                                                        │
   └──── reads state ◄── adapters.js converts JSON ◄──────────── JSON response ◄────────┘
```

| File | Role |
|---|---|
| `src/api.js` | **Central API client.** Base URL (`/api`, proxied to Flask by Vite), JWT header, JSON parsing, readable `ApiError` messages, and automatic sign-out on 401. One small function per endpoint (`apiCreateRequest`, `apiDecide`, …). Abhinava's function names are kept. |
| `src/composables/adapters.js` | Converts backend JSON (snake_case, numeric ids, ISO dates, enum values) into the shapes the pages already used (camelCase, **string** ids, millisecond times, UI labels). This is why page templates did not need to change. |
| `src/composables/useStore.js` | Same exported function names as before, but Sprint 1 functions now call the API and then reload the affected data. `state` is now a **cache** of server data. Functions that the server now handles return the server's error message (or `null` on success). |
| `src/main.js` | Calls `initSession()` before mounting. A saved token is checked with `GET /auth/me`, so refreshing the page keeps you signed in. |
| `vite.config.js` | Proxies `/api` to `http://127.0.0.1:5000`. |

### Loading data
After login (and on refresh), `refresh()` loads what the signed-in role needs:

| Role | Calls |
|---|---|
| everyone | `GET /auth/me`, `GET /notifications`, `GET /tags` (admins: `GET /admin/tags`), `GET /requests`, `GET /mentoring` |
| student, coordinator, admin | `GET /mentors?page_size=100` (verified mentors for the directory) |
| admin | `GET /admin/users` |

User summaries embedded in requests and mentorships are cached in `state.users`, so a mentor
sees student names, and a student sees their mentors' names. Signed out, the app still loads
`GET /tags` (public), because the registration form needs the tag list.

### Authentication and JWT in the browser
* `login()` → `POST /auth/login` → the token is saved in `localStorage["mentorconnect_token"]`.
* Every request adds `Authorization: Bearer <token>`.
* If the server answers 401 (expired or invalid token, or account blocked), `api.js` calls the handler
  registered in `initSession()`: it clears the cached data and the token, shows "session expired" and goes to `#/login`.
* `logout()` deletes the token and the cached data.

## Page-to-API map

| Page / component | API endpoint(s) | Component | Tables | Status |
|---|---|---|---|---|
| LoginPage (incl. demo buttons) | `POST /auth/login`, `GET /auth/me` | C1 | users | ✅ connected, verified in browser |
| RegisterPage (student & mentor) | `POST /auth/register`, `GET /tags` | C1, C3 | users, student, mentor, user_tags | ✅ verified in browser (mentor) |
| StudentProfilePage | `PUT /profile/me`, `PUT /profile/me/tags` | C2, C3 | users, student, user_tags | ✅ verified in browser |
| MentorProfilePage | `PUT /profile/me`, `PUT /profile/me/tags` | C2, C3 | mentor, user_tags | ✅ connected (API tested; UI not clicked through) |
| MentorDashboardPage: capacity & pause | `PUT /profile/me` (`mentor.capacity`, `mentor.pause`) | C2 | mentor | ✅ verified in browser |
| AccountExtras: username, photo | `PUT /profile/me` | C2 | users | ✅ connected (API tested) |
| ChangePassword | `POST /auth/change-password` | C1 | users | ✅ connected (API tested) |
| MentorDirectoryPage, MentorCard | `GET /mentors` | C4 | users, mentor, user_tags, request, mentorship | ✅ verified in browser |
| MentorDetailsPage | data from `GET /mentors` | C4 | – | ✅ (availability and public feedback panels are Sprint 2, browser-only) |
| MentoringRequestPage | `POST /requests` | C5 | request, request_status_history, Notifications | ✅ verified in browser |
| StudentRequestsPage (tabs, timeline, withdraw) | `GET /requests`, `POST /requests/{id}/withdraw` | C5 | request, request_status_history | ✅ list verified in browser; withdraw API tested |
| IncomingRequestsPage, RequestReviewPage | `GET /requests`, `POST /requests/{id}/decision` | C5, C6 | request, mentorship | ✅ accept verified in browser; reject API tested |
| MyMenteesPage, dashboards' mentee lists | `GET /mentoring` | C6 | mentorship | ✅ connected |
| NotificationsPage, nav badge | `GET /notifications`, `PATCH …/read`, `PATCH /notifications/read-all` | C13 | Notifications | ✅ verified in browser |
| SuggestTagModal | `POST /tags/suggest` | C3 | tag | ✅ connected (API tested) |
| AdminContent: approve, reject, new tag | `PATCH /admin/tags/{id}`, `POST /admin/tags` | C3 | tag | ✅ approve verified in browser |
| AdminContent: merge tags | – | C3 | – | ❌ shows "not connected yet" (D-07) |
| AdminUsers: verify mentor | `PATCH /admin/mentors/{id}/verification` | C14 | mentor | ✅ verified in browser |
| AdminUsers: block/unblock, purge | – | C14 | – | ⏳ browser-only (Sprint 2) |
| CareerGoalsPage, CoordinatorGoalsPage | – | C7 | (trackgoal ready) | ⏳ browser-only, saved in localStorage |
| AvailabilityPage | – | C8 | (availability ready) | ⏳ browser-only |
| SessionsPage (booking, notes, action items) | – | C9, C10 | (session, session_action_items ready) | ⏳ browser-only |
| FeedbackPage, AccountPage platform feedback | – | C11 | (feedback, platform_feedback ready) | ⏳ browser-only |
| AccountPage: report a user, delete account | – | C12, C14 | (report_user ready) | ⏳ browser-only |
| CoordinatorDashboard / Matching / Profile to-dos | `GET /requests` (stuck requests, no messages) | C15 | – | 🟡 stuck-request list from the API; matching and to-dos browser-only |
| AdminDashboard overview | `GET /requests`, `GET /mentoring`, `GET /admin/users` | C15 | – | 🟡 figures computed in the browser from API data |

## What was changed in the frontend (and why)

| File | Change |
|---|---|
| `src/api.js` | Rewritten as the central client (was FastAPI-only, port 8000, form login). |
| `src/composables/adapters.js` | **New.** Server-to-UI translation. |
| `src/composables/useStore.js` | Sprint 1 functions call the API. Sprint 2 slices persist in `localStorage` (`mentorconnect_local_v1`). Expiry, reminders and purge are server-side now (no-ops in the browser). Added `refresh`, `initSession`, `saveMentorSettings`, `markRead`, `markAllRead`, `approveTag`, `rejectTag`, `activeCount`, `userTodos`. |
| `src/main.js` | Waits for `initSession()` before mounting. |
| `vite.config.js` | `/api` proxy. |
| `utils/helpers.js` | Reverse employment label fix (`standalone` → "Studying only", D-05). |
| Pages/components | Only the script parts changed: functions became `async`/`await` (the API takes time), direct edits of data (`u.capacity = …`, `n.read = true`, `t.status = 'approved'`) became API calls, `MentorCard`/`MentorDetailsPage` use `activeCount(m)` (the server's mentee count), and the request page shows "Sending…". **No templates, styles, routes or layouts were redesigned.** |

## Known frontend limitations
* Sprint 2 features keep data per browser (localStorage), not in the database. Clearing site data deletes it.
* Notifications created by browser-only features (for example a session request) are not saved on the server and vanish on the next refresh.
* The directory loads up to 100 verified mentors and filters them on the page for instant results. The server-side filters exist and are tested, but the page does not call them yet.
