"""Sprint 1 edge cases added for the Milestone 3 submission.

Covers the gaps found in the submission audit: unauthenticated access (401) on every
protected endpoint, boundary values from the M1 acceptance criteria, admin-only routes,
the request status filter, and notifications for every request event (US-06/US-08).
"""

import pytest

from tests.conftest import MSG, auth, login_as

# Every protected Sprint 1 endpoint must refuse a request without a token (M1 US-01: "Unauthorized access returns a 401").
PROTECTED = [
    ("get", "/api/auth/me"), ("post", "/api/auth/change-password"), ("post", "/api/auth/logout"),
    ("get", "/api/profile/me"), ("put", "/api/profile/me"), ("put", "/api/profile/me/tags"),
    ("get", "/api/mentors"), ("get", "/api/mentors/1"), ("get", "/api/students/1/card"),
    ("post", "/api/tags/suggest"), ("get", "/api/admin/tags"), ("post", "/api/admin/tags"), ("patch", "/api/admin/tags/1"),
    ("post", "/api/requests"), ("get", "/api/requests"), ("get", "/api/requests/1"),
    ("post", "/api/requests/1/withdraw"), ("post", "/api/requests/1/decision"),
    ("get", "/api/mentoring"), ("get", "/api/admin/users"), ("patch", "/api/admin/mentors/1/verification"),
]


@pytest.mark.parametrize("method,url", PROTECTED)
def test_protected_endpoints_require_token(seeded, method, url):
    resp = getattr(seeded, method)(url, json={})
    assert resp.status_code == 401
    assert resp.get_json()["error"]["status"] == 401


def test_logout_with_token(seeded):
    h = auth(seeded, "student@mentorconnect.demo")
    assert seeded.post("/api/auth/logout", headers=h).get_json() == {"message": "Signed out."}


# ---------------- boundary values (US-01, US-03, US-06, US-08) ----------------

def _student(email, username, password):
    return {"email": email, "password": password, "role": "student", "name": "Edge Student", "username": username}


def test_password_boundary_7_and_8_characters(seeded):
    assert seeded.post("/api/auth/register", json=_student("e1@ds.study.iitm.ac.in", "edge_1", "Abc1234")).status_code == 400
    assert seeded.post("/api/auth/register", json=_student("e2@ds.study.iitm.ac.in", "edge_2", "Abcd1234")).status_code == 201


def test_mentor_capacity_boundary_10_and_expertise_limit_6(seeded):
    base = {"password": "Secret123", "role": "mentor", "name": "Edge Mentor", "designation": "Dev", "company": "Acme"}
    six = ["Data Science", "Machine Learning", "Career Switch", "Backend", "System Design", "Internships"]
    ok = seeded.post("/api/auth/register", json={**base, "email": "em1@x.com", "username": "em_1", "capacity": 10, "expertise": six})
    assert ok.status_code == 201 and ok.get_json()["mentor"]["capacity"] == 10 and len(ok.get_json()["tags"]) == 6
    too_many = seeded.post("/api/auth/register", json={**base, "email": "em2@x.com", "username": "em_2", "capacity": 2,
                                                       "expertise": six + ["Research"]})
    assert too_many.status_code == 400
    h = auth(seeded, "mentor@mentorconnect.demo")
    assert seeded.put("/api/profile/me/tags", headers=h, json={"names": six}).status_code == 200
    assert seeded.put("/api/profile/me/tags", headers=h, json={"names": six + ["Research"]}).status_code == 400


def test_message_exact_boundaries_50_and_1500(client, make):
    _, semail = make.student()
    m1, _ = make.mentor()
    m2, _ = make.mentor()
    h = login_as(client, semail)
    assert client.post("/api/requests", headers=h, json={"mentor_id": m1, "student_message": "a" * 50}).status_code == 201
    assert client.post("/api/requests", headers=h, json={"mentor_id": m2, "student_message": "b" * 1500}).status_code == 201


def test_reject_reason_exactly_500_characters(client, make):
    _, semail = make.student()
    mid, memail = make.mentor()
    rid = client.post("/api/requests", headers=login_as(client, semail), json={"mentor_id": mid, "student_message": MSG}).get_json()["id"]
    r = client.post(f"/api/requests/{rid}/decision", headers=login_as(client, memail), json={"action": "reject", "reason": "r" * 500})
    assert r.status_code == 200 and len(r.get_json()["mentor_response"]) == 500
    assert r.get_json()["history"][-1] == {**r.get_json()["history"][-1], "to": "rejected", "actor": "Mentor"}


# ---------------- request listing (US-07) ----------------

def test_request_status_filter_and_invalid_status(seeded):
    h = auth(seeded, "student@mentorconnect.demo")
    pending = seeded.get("/api/requests?status=pending", headers=h).get_json()
    assert pending and all(r["status"] == "pending" for r in pending)
    assert seeded.get("/api/requests?status=banana", headers=h).status_code == 400


def test_student_quota_is_freed_after_expiry(app, client, make):
    """US-09 preview / US-06: expired requests no longer count towards the 3-pending limit."""
    from datetime import timedelta

    from app.extensions import db
    from app.models import Request, utcnow
    _, semail = make.student()
    mentors = [make.mentor()[0] for _ in range(4)]
    h = login_as(client, semail)
    ids = [client.post("/api/requests", headers=h, json={"mentor_id": m, "student_message": MSG}).get_json()["id"] for m in mentors[:3]]
    assert client.post("/api/requests", headers=h, json={"mentor_id": mentors[3], "student_message": MSG}).status_code == 409
    with app.app_context():
        db.session.get(Request, ids[0]).expires_on = utcnow() - timedelta(minutes=1)
        db.session.commit()
    assert client.post("/api/requests", headers=h, json={"mentor_id": mentors[3], "student_message": MSG}).status_code == 201


# ---------------- notifications for every request event (US-06, US-08) ----------------

def test_notifications_for_accept_withdraw_and_auto_close(client, make):
    sid, semail = make.student()
    m1, m1email = make.mentor(name="Mentor One")
    m2, m2email = make.mentor(name="Mentor Two")
    m3, m3email = make.mentor(name="Mentor Three")
    hs = login_as(client, semail)
    r1 = client.post("/api/requests", headers=hs, json={"mentor_id": m1, "student_message": MSG}).get_json()["id"]
    r2 = client.post("/api/requests", headers=hs, json={"mentor_id": m2, "student_message": MSG}).get_json()["id"]
    r3 = client.post("/api/requests", headers=hs, json={"mentor_id": m3, "student_message": MSG}).get_json()["id"]
    client.post(f"/api/requests/{r3}/withdraw", headers=hs)
    client.post(f"/api/requests/{r1}/decision", headers=login_as(client, m1email), json={"action": "accept"})
    msgs = lambda email: [n["message"] for n in client.get("/api/notifications", headers=login_as(client, email)).get_json()]  # noqa: E731
    assert any("withdrew" in m for m in msgs(m3email))
    assert any("accepted your mentoring request" in m for m in msgs(semail))
    assert any("matched with another mentor" in m for m in msgs(m2email))
    notes = client.get("/api/notifications", headers=hs).get_json()
    assert any(n["rid"] == r1 for n in notes)  # US-13: notification identifies the request
    assert client.get(f"/api/requests/{r2}", headers=hs).get_json()["history"][-1]["actor"] == "System"


# ---------------- role checks on Sprint 1 admin/profile routes ----------------

def test_mentor_cannot_open_mentor_profile(seeded):
    h = auth(seeded, "mentor@mentorconnect.demo")
    assert seeded.get("/api/mentors/1", headers=h).status_code == 403


def test_admin_verification_errors(seeded):
    admin = auth(seeded, "admin@mentorconnect.demo")
    users = {u["email"]: u["id"] for u in seeded.get("/api/admin/users", headers=admin).get_json()}
    isha = users["isha.verma@alumni.demo"]
    assert seeded.patch(f"/api/admin/mentors/{isha}/verification", headers=admin, json={"status": "approved"}).status_code == 400
    assert seeded.patch(f"/api/admin/mentors/{users['student@mentorconnect.demo']}/verification", headers=admin,
                        json={"status": "verified"}).status_code == 404
    student = auth(seeded, "student@mentorconnect.demo")
    assert seeded.patch(f"/api/admin/mentors/{isha}/verification", headers=student, json={"status": "verified"}).status_code == 403
    h_isha = auth(seeded, "isha.verma@alumni.demo")
    seeded.put("/api/profile/me", headers=h_isha, json={"mentor": {"designation": "", "company": ""}})
    r = seeded.patch(f"/api/admin/mentors/{isha}/verification", headers=admin, json={"status": "verified"})
    assert r.status_code == 400 and "not completed" in r.get_json()["error"]["message"]


def test_admin_tag_errors(seeded):
    admin = auth(seeded, "admin@mentorconnect.demo")
    assert seeded.patch("/api/admin/tags/99999", headers=admin, json={"action": "approve"}).status_code == 404
    tag = seeded.get("/api/tags").get_json()[0]
    assert seeded.patch(f"/api/admin/tags/{tag['id']}", headers=admin, json={}).status_code == 400
    assert seeded.patch(f"/api/admin/tags/{tag['id']}", headers=admin, json={"action": "reject"}).status_code == 400
    assert seeded.post("/api/admin/tags", headers=admin, json={"name": tag["name"].upper()}).status_code == 409
    assert seeded.get("/api/tags?type=colour").status_code == 400


def test_staff_cannot_select_tags_and_duplicates_rejected(seeded):
    assert seeded.put("/api/profile/me/tags", headers=auth(seeded, "admin@mentorconnect.demo"), json={"names": ["Data Science"]}).status_code == 400
    h = auth(seeded, "student@mentorconnect.demo")
    tid = seeded.get("/api/tags").get_json()[0]["id"]
    assert seeded.put("/api/profile/me/tags", headers=h, json={"tags": [{"tag_id": tid}, {"tag_id": tid}]}).status_code == 400


def test_coordinator_sees_student_card_without_contact_details(seeded):
    priya = auth(seeded, "mentor@mentorconnect.demo")
    sid = next(r["sid"] for r in seeded.get("/api/requests", headers=priya).get_json() if r["status"] == "pending")
    card = seeded.get(f"/api/students/{sid}/card", headers=auth(seeded, "coordinator@mentorconnect.demo")).get_json()
    assert card["email"] is None and card["phone"] is None


def test_directory_returns_support_types_and_titles(seeded):
    """US-05: results display mentor name, job title, and support types offered."""
    h = auth(seeded, "student@mentorconnect.demo")
    items = seeded.get("/api/mentors", headers=h).get_json()["items"]
    assert all(m["name"] and m["mentor"]["designation"] and m["mentor"]["support_types"] for m in items)
    assert seeded.get("/api/mentors?page=abc", headers=h).status_code == 400
