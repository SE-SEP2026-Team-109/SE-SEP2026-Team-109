# Testing report

Last run: **21 Nov 2026**, branch `feature/flask-backend-integration`, Windows 10, Python 3.11.9, Node 22.20.

| Suite | Command | Result |
|---|---|---|
| Backend unit + integration (pytest) | `cd backend && venv\Scripts\python -m pytest` | **53 passed, 0 failed** (≈ 60 s) |
| Mutation check (do the tests catch broken rules?) | Temporarily set the pending limit to 4 and the minimum message to 5 characters | 2 tests failed as expected (`test_three_pending_limit_and_duplicate`, `test_message_length_rules`); rules restored and suite green again |
| Frontend production build | `cd frontend && npx vite build` | Builds with no errors |
| End-to-end in a real browser (Flask + Vite running) | manual, steps below | All Sprint 1 flows passed; 1 bug found and fixed |

Every test uses a **fresh in-memory database** (`tests/conftest.py`). Tests never touch `instance/mentorconnect.db`.

## 1. Backend tests: case → expected result

All rows below were executed, and the actual result equalled the expected result (pass).

### C1 Auth (`tests/test_auth.py`)
| Test | Expected |
|---|---|
| `test_health` | `GET /api/health` → `{"status":"ok"}` |
| `test_student_registration_creates_profile_and_hides_password` | 201; student row + interest tag created; no password anywhere in the response |
| `test_student_must_use_iitm_email` | gmail address → 400 mentioning study.iitm.ac.in |
| `test_password_needs_letters_and_numbers` | `short1`, `allletters`, `12345678` → 400 each |
| `test_duplicate_email_and_username` | second registration with the same email or username → 409 |
| `test_coordinator_and_admin_cannot_self_register` | role admin → 400 |
| `test_mentor_registration_pending_and_admin_notified` | mentor `veri_status` pending, pause false; admin receives a notification |
| `test_mentor_capacity_required_and_limited` | missing / 11 / 0 → 400 |
| `test_unapproved_tag_rejected_at_registration` | suggested (unapproved) tag → 400 |
| `test_login_success_and_me` | token works on `/auth/me` |
| `test_login_accepts_form_fields_for_old_client` | form-encoded login → 200 |
| `test_wrong_password_and_unknown_email` | both → 401 |
| `test_missing_and_invalid_token` | 401 |
| `test_expired_token_rejected` | expired JWT → 401 "expired" |
| `test_blocked_user_cannot_log_in_or_use_token` | deactivated: login 403, existing token 401 |
| `test_change_password` | wrong current → 400; correct → 200; new password works |

### C2 Profile, C3 Tags, C4 Directory (`tests/test_profile_tags_directory.py`)
| Test | Expected |
|---|---|
| `test_student_updates_own_profile` | fields saved and still there on the next GET |
| `test_foundation_clears_course_level` | courselevel null |
| `test_student_cannot_send_mentor_fields_and_unknown_fields_rejected` | 400 / 400 |
| `test_mentor_capacity_and_pause` | 5 + pause saved; 11 and 0 → 400 |
| `test_username_must_be_unique` | 409 |
| `test_photo_validation` | `javascript:` → 400; data URL → 200 |
| `test_tag_limits_and_approval` | 6 tags → 400; pending tag → 400; 5 approved → 200 |
| `test_email_hidden_until_accepted` | pending student sees null email; accepted student sees it |
| `test_student_card_access` | own requester → 200; other mentor → 404; student → 403 |
| `test_unverified_mentor_profile_is_404_for_students` | 404 |
| `test_tags_public_list_only_approved` | approved yes, suggested no |
| `test_suggest_and_admin_approve_reject` | suggest 201; duplicate 409; student approving → 403; admin approve → public; reject → removed; create → 201 |
| `test_directory_lists_only_verified_and_computes_slots` | 6 verified; full mentor `free_slots` 0 and `can_request` false; paused mentor 0 slots |
| `test_directory_filters_and_sorts` | q (company and tag), industry, area, expertise, has_slots, both sorts as expected; bad sort → 400 |
| `test_directory_pagination_and_roles` | page 2 of 2 has 2 items; mentor → 403 |
| `test_admin_verifies_mentor_then_visible` | verified mentor appears in the student directory; student on admin route → 403 |

### C5 Requests, C6 Mentoring, C13 Notifications (`tests/test_requests_mentoring.py`)
| Test | Expected |
|---|---|
| `test_submit_request_records_history_expiry_and_notifies` | 201, history `[pending by Student]`, expiry exactly 14 days later, mentor notified |
| `test_message_length_rules` | <50, >1500, 49-after-trim → 400 |
| `test_three_pending_limit_and_duplicate` | 4th request → 409 "3 pending" |
| `test_duplicate_pending_to_same_mentor` | 409 |
| `test_paused_full_and_unverified_mentors` | paused → 409; unverified → 404; missing → 404 |
| `test_only_students_create_for_themselves` | mentor → 403; student for another student → 403 |
| `test_withdraw_frees_quota_and_is_terminal` | withdrawn by Student; second withdraw → 409; quota freed |
| `test_privacy_404_for_other_users_requests` | other student/mentor: GET, withdraw, decide → 404 |
| `test_reject_with_optional_reason` | reject without a reason → 200; decided → 409; re-request allowed; 501-character reason → 400; reason saved; student notified |
| `test_accept_creates_mentorship_unmasks_and_closes_other_requests` | email masked before, visible after; other request withdrawn by System; mentorship listed; new request → 409 |
| `test_accept_rechecks_capacity_409` | second accept at capacity 1 → 409; new request to full mentor → 409 |
| `test_lowering_capacity_keeps_existing_mentorship` | mentorship still active |
| `test_expiry_marks_system_and_frees_quota` | overdue → expired by System; mentor notified; saved in DB |
| `test_run_jobs_cli` | `flask run-jobs` expires 1 request |
| `test_staff_see_requests_without_messages` | admin and coordinator see 7 requests, all messages null |
| `test_coordinator_assignment_still_needs_mentor_acceptance` | source coordinator, status pending |
| `test_mutual_end` | first end → still active; repeat → 409; second party → inactive |
| `test_cancel_end_request` | cancel without request → 409; after request → cleared |
| `test_end_auto_after_15_days` | job ends 1 mentorship |
| `test_mentoring_privacy` | outsider → 404 |
| `test_notifications_read_and_privacy` | other user's notification → 404; mark read; read-all |

## 2. End-to-end browser test (real UI, real database)

Setup: `python backend/run.py` (fresh seeded DB) and `npm run dev` in `frontend`; browser at http://localhost:5173.
Some form fields were filled by a script that fires the same input/click events a user would. Every result was then confirmed through the UI **and** the API.

| # | Flow | Observed result |
|---|---|---|
| 1 | Click "Explore with the demo student account" | Signed in as Aarav, student dashboard ✅ |
| 2 | Open Mentors | 6 verified mentors from the DB; "2 of 3 places free" for Priya (1 mentee), Rahul "All places taken", Vikram "Paused" ✅ |
| 3 | Request Neha Kulkarni (122-character message) | Redirected to My requests; new pending request "Expires 5 Dec 2026" (14 days) ✅. The seeded 15-day-old request to Dr. Seth showed **Expired** (lazy expiry, actor System) ✅ |
| 4 | Reload the page | Still signed in, same data (JWT restored from localStorage) ✅ |
| 5 | Sign out, sign in as `neha.kulkarni@alumni.demo` | Incoming requests shows Aarav's request; student email "Hidden until you accept" ✅ |
| 6 | Accept | Status Accepted; email now visible; "1 of 3 used"; history "Pending by Student → Accepted by Mentor" ✅ |
| 7 | API check as Aarav | Priya request **withdrawn by System**; active mentorship with Neha; notification "Neha Kulkarni accepted…" ✅ |
| 8 | Neha dashboard: capacity 4, pause on, then off | Saved in DB (`capacity 4`, `pause true`, then false); toasts shown ✅ |
| 9 | Notifications → Mark all as read | UI and DB both show 0 unread ✅ |
| 10 | Register a new mentor through the form | **Bug found:** no expertise chips → blocked by "Choose at least 1 area of expertise". Fixed (see §3). After the fix: registered → success page ✅ |
| 11 | Admin signs in → Users → Verify the new mentor | Row changes Unverified → Active; toast ✅; a student now finds the mentor with `q=pipeworks` ✅ |
| 12 | Admin → Content → Approve "UX Design" | Appears in public `GET /tags` ✅ |
| 13 | Student Sneha edits profile (adds NLP interest, new skill, needs) | Saved in DB (tags, skills, needs), shown after reload ✅ |
| 14 | Goals page (Sprint 2, browser-only) | Adding a goal works and is kept in localStorage ✅ |
| – | Browser console | No errors during the whole session ✅ |

## 3. Errors found and how they were fixed

| Problem | Cause | Fix |
|---|---|---|
| Registration page had no expertise/interest chips | The tag list was loaded only after login, but registration happens before login | `initSession()` loads the public `GET /tags` when signed out, and sign-out keeps the approved tag list |
| Profile showed "Currently: Between jobs" for a student who only studies | "Studying only" and "Between jobs" both map to `standalone`; the reverse lookup took the last one | Reverse mapping now prefers "Studying only" (decision D-05 records the underlying gap) |
| Shell quoting broke a long scripted edit (tooling, not product) | Bash heredoc quoting | Script moved into a file |

No failing tests remain.

## 4. Not tested / partially tested (honest list)

* **Two simultaneous accepts in parallel** (true concurrency) were not run. The SQLite lock (D-15) is in place, and the sequential capacity re-check is tested.
* **UI click-through not done** for: mentor profile edit form, username change, photo upload, change-password form, student withdraw button, reject button, tag suggestion modal, student registration form. Their API calls are covered by the backend tests.
* **Coordinator UI** was not exercised in the browser.
* **Token expiry in the browser** (auto sign-out after 120 minutes) was not observed live; the backend 401 for expired tokens is tested.
* **All Sprint 2 components (C7–C12, most of C14/C15/C16)** have no backend implementation, so nothing to test server-side.
* No automated frontend tests (none existed before). A Vitest/Playwright suite is suggested for Sprint 2.

## 5. How to run the tests yourself

```powershell
cd backend
venv\Scripts\python -m pytest            # all tests
venv\Scripts\python -m pytest -k request # only tests with "request" in the name
venv\Scripts\python -m pytest -x -vv     # stop at the first failure, show details
```
