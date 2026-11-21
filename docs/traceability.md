# Milestone traceability

Maps every Milestone 1 user story and acceptance criterion to the Milestone 2 component and the code/tests that implement it.
A row is marked **Done** only if it is implemented *and* tested. Status: ✅ Done · 🟡 Partial · ⏳ Not started (Sprint 2) · ↔ Deviation (see [decisions.md](decisions.md)).

## Sprint 1 (Milestone 3): US-01 to US-08

| Story / acceptance criterion | M2 component | Implementation | Tests | Status |
|---|---|---|---|---|
| **US-01** Register and sign in with role-based access | C1 | `auth_service`, `security`, `routes/auth.py` | test_auth.py | ✅ |
| – Student email must be @study.iitm.ac.in | C1 | `auth_service._is_iitm_student_email` | `test_student_must_use_iitm_email` | ✅ |
| – Password ≥ 8, alphanumeric | C1 | `schemas.check_password` | `test_password_needs_letters_and_numbers` | ✅ |
| – Login returns JWT; unauthorised → 401 | C1 | `security` | `test_login_success_and_me`, `test_missing_and_invalid_token`, `test_expired_token_rejected` | ✅ |
| – Redirect to the role's dashboard | frontend | `LoginPage` → `home(role)` | browser E2E #1, #5, #11 | ✅ |
| – Deactivated/blacklisted/to-be-deleted cannot log in (M2 C1) | C1 | `auth_service.login`, `security._load_current_user` | `test_blocked_user_cannot_log_in_or_use_token` | ✅ |
| **US-02** Student mentoring profile | C2, C3 | `profile_service`, `set_tags` | test_profile_tags_directory.py | ✅ |
| – Create, view, update own profile | C2 | `PUT/GET /profile/me` | `test_student_updates_own_profile`, E2E #13 | ✅ |
| – Mentors cannot see student email until accepted | C2 | `dto.can_see_contact` | `test_email_hidden_until_accepted`, `test_accept_creates_mentorship_unmasks…`, E2E #5–6 | ✅ |
| – Empty mandatory fields fail gracefully | C2 + UI | Pydantic 400 + page validation | `test_student_cannot_send_mentor_fields…` | ✅ |
| – 1–5 expertise areas | C3 | `set_tags` limit 5 | `test_tag_limits_and_approval` | ✅ |
| **US-03** Mentor profile | C2, C3 | `auth_service.register`, `profile_service` | test_auth, test_profile… | ✅ |
| – Up to 6 expertise areas from a predefined list | C3 | approved tags only, ≤ 6 | `test_unapproved_tag_rejected_at_registration`, `test_tag_limits_and_approval` | ✅ |
| – Profile visible to authenticated students only | C2 | `@roles_required` on `/mentors/{id}` | `test_directory_pagination_and_roles` (mentor 403) | ✅ |
| – Initial capacity 1–10 at creation | C1/C2 | `RegisterIn.capacity` | `test_mentor_capacity_required_and_limited` | ✅ ↔ D-02 |
| – Support types | C2 | `mentor.support_types` | `test_mentor_registration_pending…` | ✅ ↔ D-09 |
| – Hidden from search until verified (M2 C2) | C2/C4/C14 | `veri_status`, admin verification | `test_admin_verifies_mentor_then_visible`, E2E #11 | ✅ ↔ D-17 |
| **US-04** Manage capacity | C2, C5 | `PUT /profile/me` mentor.capacity/pause | `test_mentor_capacity_and_pause`, E2E #8 | ✅ |
| – Capacity 1–10 | C2 | schema | `test_mentor_capacity_and_pause` | ✅ ↔ D-02 |
| – Full → "No open slots", request disabled | C4 + UI | `free_slots`, `can_request`, `MentorCard` | `test_directory_lists_only_verified…`, E2E #2 | ✅ |
| – Lowering capacity does not cancel mentorships | C5/C6 | no cascade | `test_lowering_capacity_keeps_existing_mentorship` | ✅ |
| – Pause toggle | C2 | `mentor.pause` | `test_mentor_capacity_and_pause`, `test_paused_full_and_unverified_mentors` | ✅ ↔ D-03 |
| **US-05** Search mentors | C4 | `directory_service.search` | `test_directory_filters_and_sorts` | ✅ |
| – Filters career area, industry, "has open slots"; paginated | C4 | query params | `test_directory_filters_and_sorts`, `test_directory_pagination_and_roles` | ✅ ↔ D-09 |
| – Results show name, title, support types | C4 + UI | User DTO, `MentorCard` | E2E #2 | ✅ |
| – Paused mentors show a 'Paused' badge | UI | `MentorCard` | E2E #2 | ✅ |
| – Empty result "Try adjusting your filters" | UI | `EmptyState` | (existing UI, not re-tested) | 🟡 |
| **US-06** Submit request | C5 | `request_service.create` | test_requests_mentoring.py | ✅ |
| – 50–1500 characters | C5 | `RequestCreate` | `test_message_length_rules` | ✅ |
| – Max 3 pending system-wide | C5 | `count_pending_requests` | `test_three_pending_limit_and_duplicate` | ✅ |
| – Not to a mentor at capacity | C5 | capacity check with lock | `test_accept_rechecks_capacity_409` | ✅ |
| – Timestamp + expiry 14 days | C5 | `expires_on` | `test_submit_request_records_history_expiry…`, E2E #3 | ✅ ↔ D-04 |
| – Mentor notified | C13 | `notify` | same test | ✅ |
| **US-07** Track request status | C5 | `GET /requests`, history | – | ✅ |
| – Full history/timeline | C5 | `request_status_history` | `test_submit_request…`, `test_accept_creates…`, E2E #6–7 | ✅ ↔ D-08 |
| – Withdraw pending, frees quota | C5 | `withdraw` | `test_withdraw_frees_quota_and_is_terminal` | ✅ |
| – Grouped by status | UI | tabs | E2E #3 | ✅ |
| **US-08** Review and decide | C5, C6 | `decide` | – | ✅ |
| – Accept reveals emails both ways | C2/C5 | masking | `test_accept_creates_mentorship_unmasks…`, E2E #6 | ✅ |
| – Optional reason ≤ 500 | C5 | `RequestDecision` | `test_reject_with_optional_reason` | ✅ ↔ D-01 |
| – Decided cannot revert | C5 | status check | `test_reject_with_optional_reason` | ✅ |
| – Atomic transaction, notifications | C5 | single commit | `test_accept_creates…` | ✅ |
| M1 edge case 1: simultaneous last slot → 409 | C5 | `lock_mentor` + re-check | `test_accept_rechecks_capacity_409` (sequential) | 🟡 ↔ D-15 (no parallel test) |
| M1 edge case 4 / §4.2: others' records → 404 | all | participant checks | `test_privacy_404…`, `test_mentoring_privacy`, `test_notifications_read_and_privacy` | ✅ |

## Sprint 2 (Milestone 4): US-09 to US-16

| Story | Component | Status | What exists now |
|---|---|---|---|
| US-09 Automated expiry | C5, C16 | 🟡 | Expiry to *expired* by System, with history and notifications to both: done and tested (lazy + `run-jobs`). The quota refund is automatic because pending requests are counted. A scheduled run (cron) still needs to be set up. |
| US-10 Career goals | C7 | ⏳ | Table `trackgoal` (with `todo`). UI works browser-only. Reference: FastAPI branch `origin/goals`. |
| US-11 Platform participation | C15 | ⏳ | Admin overview computed in the browser from API data; no `/insights/stats` API. |
| US-12 Session feedback & action items | C9–C11 | ⏳ | Tables ready; UI browser-only. |
| US-13 Notifications | C13 | 🟡 | List, mark read, privacy: done and tested. Generated for request events; Sprint 2 events (sessions, admin actions) pending. |
| US-14 Account deletion | C14 | ⏳ | `users.status`/`delete_time` columns; UI browser-only. |
| US-15 Report behaviour | C12 | ⏳ | Table `report_user` (nullable mgid, reported_user); UI browser-only. |
| US-16 Mentor availability | C8 | ⏳ | Table `availability`; UI browser-only. |

## Components summary

| Component | Implemented | Tested | Frontend integrated | Remaining |
|---|---|---|---|---|
| C1 Auth | ✅ | ✅ | ✅ | – |
| C2 Profile | ✅ | ✅ | ✅ | real photo upload endpoint (D-11) |
| C3 Tags | ✅ | ✅ | ✅ (merge not connected) | merge API (D-07) |
| C4 Directory | ✅ | ✅ | ✅ | page filters locally on server data |
| C5 Requests | ✅ | ✅ | ✅ | parallel-race test |
| C6 Mentoring | ✅ | ✅ | 🟡 (lists yes; no "end mentorship" button exists in the UI) | UI for ending |
| C7–C12 | ⏳ | – | browser-only | Sprint 2 |
| C13 Notifications | ✅ | ✅ | ✅ | Sprint 2 event types |
| C14 Account lifecycle | 🟡 (verify, list) | ✅ for what exists | 🟡 | deactivate/blacklist/deletion/anonymise |
| C15 Insights & matching | ⏳ (assignment via C5 only) | partial | 🟡 | aggregate and candidate APIs |
| C16 Scheduler | 🟡 (expiry, auto-end) | ✅ | n/a | reminders, complete sessions, purge, cron |
