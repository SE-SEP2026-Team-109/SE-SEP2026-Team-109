"""C5 Requests (US-06, US-07, US-08, US-09 expiry), C6 Mentoring, C13 Notifications."""

from datetime import timedelta

from app.extensions import db
from app.models import Request, RequestStatus, utcnow
from tests.conftest import MSG, auth, login_as


def send(client, h, mentor_id, msg=MSG):
    return client.post("/api/requests", headers=h, json={"mentor_id": mentor_id, "student_message": msg})


def test_submit_request_records_history_expiry_and_notifies(client, make):
    sid, semail = make.student()
    mid, memail = make.mentor()
    hs = login_as(client, semail)
    r = send(client, hs, mid)
    assert r.status_code == 201
    body = r.get_json()
    assert body["status"] == "pending" and body["history"] == [
        {"from": None, "to": "pending", "actor": "Student", "at": body["history"][0]["at"]}]
    from datetime import datetime
    created = datetime.fromisoformat(body["created_on"].rstrip("Z"))
    expires = datetime.fromisoformat(body["expires_on"].rstrip("Z"))
    assert (expires - created).days == 14
    hm = login_as(client, memail)
    assert any("New mentoring request" in n["message"] for n in client.get("/api/notifications", headers=hm).get_json())


def test_message_length_rules(client, make):
    _, semail = make.student()
    mid, _ = make.mentor()
    hs = login_as(client, semail)
    assert send(client, hs, mid, "too short").status_code == 400
    assert send(client, hs, mid, "x" * 1501).status_code == 400
    assert send(client, hs, mid, "   " + "y" * 49 + "   ").status_code == 400  # 49 after trimming


def test_three_pending_limit_and_duplicate(client, make):
    _, semail = make.student()
    mentors = [make.mentor()[0] for _ in range(4)]
    hs = login_as(client, semail)
    for mid in mentors[:3]:
        assert send(client, hs, mid).status_code == 201
    assert send(client, hs, mentors[0]).status_code == 409  # limit hit first
    r = send(client, hs, mentors[3])
    assert r.status_code == 409 and "3 pending" in r.get_json()["error"]["message"]


def test_duplicate_pending_to_same_mentor(client, make):
    _, semail = make.student()
    mid, _ = make.mentor()
    hs = login_as(client, semail)
    send(client, hs, mid)
    assert "already have a pending request" in send(client, hs, mid).get_json()["error"]["message"]


def test_paused_full_and_unverified_mentors(client, make):
    _, semail = make.student()
    paused, _ = make.mentor(pause=True)
    from app.models import VerificationStatus
    unverified, _ = make.mentor(veri=VerificationStatus.pending)
    hs = login_as(client, semail)
    assert send(client, hs, paused).status_code == 409
    assert send(client, hs, unverified).status_code == 404
    assert send(client, hs, 9999).status_code == 404


def test_only_students_create_for_themselves(client, make):
    sid, _ = make.student()
    other, oemail = make.student()
    mid, memail = make.mentor()
    assert client.post("/api/requests", headers=login_as(client, memail), json={"mentor_id": mid, "student_message": MSG}).status_code == 403
    r = client.post("/api/requests", headers=login_as(client, oemail), json={"mentor_id": mid, "student_id": sid, "student_message": MSG})
    assert r.status_code == 403


def test_withdraw_frees_quota_and_is_terminal(client, make):
    _, semail = make.student()
    mentors = [make.mentor()[0] for _ in range(4)]
    hs = login_as(client, semail)
    ids = [send(client, hs, m).get_json()["id"] for m in mentors[:3]]
    r = client.post(f"/api/requests/{ids[0]}/withdraw", headers=hs)
    assert r.status_code == 200 and r.get_json()["status"] == "withdrawn"
    assert r.get_json()["history"][-1]["actor"] == "Student"
    assert client.post(f"/api/requests/{ids[0]}/withdraw", headers=hs).status_code == 409
    assert send(client, hs, mentors[3]).status_code == 201  # quota freed


def test_privacy_404_for_other_users_requests(client, make):
    _, semail = make.student()
    _, other_email = make.student()
    mid, _ = make.mentor()
    _, other_mentor = make.mentor()
    rid = send(client, login_as(client, semail), mid).get_json()["id"]
    for email in (other_email, other_mentor):
        h = login_as(client, email)
        assert client.get(f"/api/requests/{rid}", headers=h).status_code == 404
        assert client.post(f"/api/requests/{rid}/withdraw", headers=h).status_code == 404
        assert client.post(f"/api/requests/{rid}/decision", headers=h, json={"action": "accept"}).status_code == 404


def test_reject_with_optional_reason(client, make):
    _, semail = make.student()
    mid, memail = make.mentor()
    hs, hm = login_as(client, semail), login_as(client, memail)
    rid = send(client, hs, mid).get_json()["id"]
    r = client.post(f"/api/requests/{rid}/decision", headers=hm, json={"action": "reject"})  # no reason: allowed (M1)
    assert r.status_code == 200 and r.get_json()["status"] == "rejected"
    assert client.post(f"/api/requests/{rid}/decision", headers=hm, json={"action": "accept"}).status_code == 409
    rid2 = send(client, hs, mid).get_json()["id"]  # re-request after rejection is allowed
    long = client.post(f"/api/requests/{rid2}/decision", headers=hm, json={"action": "reject", "reason": "x" * 501})
    assert long.status_code == 400
    ok = client.post(f"/api/requests/{rid2}/decision", headers=hm, json={"action": "reject", "reason": "Calendar full"})
    assert ok.get_json()["mentor_response"] == "Calendar full"
    assert any("declined" in n["message"] for n in client.get("/api/notifications", headers=hs).get_json())


def test_accept_creates_mentorship_unmasks_and_closes_other_requests(client, make):
    sid, semail = make.student()
    m1, m1email = make.mentor()
    m2, m2email = make.mentor()
    hs = login_as(client, semail)
    rid1 = send(client, hs, m1).get_json()["id"]
    rid2 = send(client, hs, m2).get_json()["id"]
    hm1 = login_as(client, m1email)
    before = client.get(f"/api/requests/{rid1}", headers=hm1).get_json()
    assert before["student"]["email"] is None  # masked before acceptance
    r = client.post(f"/api/requests/{rid1}/decision", headers=hm1, json={"action": "accept"})
    assert r.status_code == 200 and r.get_json()["status"] == "accepted"
    assert r.get_json()["student"]["email"] == semail  # unmasked after acceptance
    other = client.get(f"/api/requests/{rid2}", headers=hs).get_json()
    assert other["status"] == "withdrawn" and other["history"][-1]["actor"] == "System"
    ms = client.get("/api/mentoring", headers=hs).get_json()
    assert len(ms) == 1 and ms[0]["mid"] == m1 and ms[0]["mentor"]["email"] == m1email
    m3, _ = make.mentor()
    assert "already have a mentor" in send(client, hs, m3).get_json()["error"]["message"]


def test_accept_rechecks_capacity_409(client, make):
    mid, memail = make.mentor(capacity=1)
    students = [make.student() for _ in range(2)]
    rids = [send(client, login_as(client, e), mid).get_json()["id"] for _, e in students]
    hm = login_as(client, memail)
    assert client.post(f"/api/requests/{rids[0]}/decision", headers=hm, json={"action": "accept"}).status_code == 200
    r = client.post(f"/api/requests/{rids[1]}/decision", headers=hm, json={"action": "accept"})
    assert r.status_code == 409 and "capacity" in r.get_json()["error"]["message"]
    # and a full mentor cannot receive new requests
    _, e3 = make.student()
    assert send(client, login_as(client, e3), mid).status_code == 409


def test_lowering_capacity_keeps_existing_mentorship(client, make):
    mid, memail = make.mentor(capacity=2)
    _, semail = make.student()
    hs, hm = login_as(client, semail), login_as(client, memail)
    rid = send(client, hs, mid).get_json()["id"]
    client.post(f"/api/requests/{rid}/decision", headers=hm, json={"action": "accept"})
    assert client.put("/api/profile/me", headers=hm, json={"mentor": {"capacity": 1}}).status_code == 200
    assert len(client.get("/api/mentoring", headers=hm).get_json()) == 1


def test_expiry_marks_system_and_frees_quota(app, client, make):
    _, semail = make.student()
    mid, memail = make.mentor()
    hs = login_as(client, semail)
    rid = send(client, hs, mid).get_json()["id"]
    with app.app_context():
        req = db.session.get(Request, rid)
        req.expires_on = utcnow() - timedelta(minutes=1)
        db.session.commit()
    body = client.get(f"/api/requests/{rid}", headers=hs).get_json()
    assert body["status"] == "expired" and body["history"][-1] == {**body["history"][-1], "actor": "System", "to": "expired"}
    assert any("expired" in n["message"] for n in client.get("/api/notifications", headers=login_as(client, memail)).get_json())
    with app.app_context():
        assert db.session.get(Request, rid).status == RequestStatus.expired


def test_run_jobs_cli(app, make):
    _, semail = make.student()
    mid, _ = make.mentor()
    c = app.test_client()
    rid = send(c, login_as(c, semail), mid).get_json()["id"]
    with app.app_context():
        db.session.get(Request, rid).expires_on = utcnow() - timedelta(days=1)
        db.session.commit()
    result = app.test_cli_runner().invoke(args=["run-jobs"])
    assert "'expired_requests': 1" in result.output


def test_staff_see_requests_without_messages(seeded):
    for email in ("admin@mentorconnect.demo", "coordinator@mentorconnect.demo"):
        h = auth(seeded, email)
        reqs = seeded.get("/api/requests", headers=h).get_json()
        assert len(reqs) == 7 and all(r["student_message"] is None for r in reqs)


def test_coordinator_assignment_still_needs_mentor_acceptance(client, make):
    sid, _ = make.student()
    mid, memail = make.mentor()
    _, cemail = make.staff("coordinator")
    r = client.post("/api/requests", headers=login_as(client, cemail), json={"mentor_id": mid, "student_id": sid, "student_message": MSG})
    assert r.status_code == 201 and r.get_json()["req_source"] == "coordinator" and r.get_json()["status"] == "pending"


# ---------------- C6 Mentoring ----------------

def _matched(client, make):
    sid, semail = make.student()
    mid, memail = make.mentor()
    hs, hm = login_as(client, semail), login_as(client, memail)
    rid = send(client, hs, mid).get_json()["id"]
    client.post(f"/api/requests/{rid}/decision", headers=hm, json={"action": "accept"})
    msid = client.get("/api/mentoring", headers=hs).get_json()[0]["id"]
    return hs, hm, msid


def test_mutual_end(client, make):
    hs, hm, msid = _matched(client, make)
    r = client.post(f"/api/mentoring/{msid}/end", headers=hs)
    assert r.status_code == 200 and r.get_json()["status"] == "active" and r.get_json()["student_end_requested_at"]
    assert client.post(f"/api/mentoring/{msid}/end", headers=hs).status_code == 409
    r = client.post(f"/api/mentoring/{msid}/end", headers=hm)
    assert r.get_json()["status"] == "inactive" and r.get_json()["end"]
    assert client.get("/api/mentoring", headers=hs).get_json() == []


def test_cancel_end_request(client, make):
    hs, hm, msid = _matched(client, make)
    assert client.post(f"/api/mentoring/{msid}/end/cancel", headers=hs).status_code == 409
    client.post(f"/api/mentoring/{msid}/end", headers=hs)
    r = client.post(f"/api/mentoring/{msid}/end/cancel", headers=hs)
    assert r.status_code == 200 and r.get_json()["student_end_requested_at"] is None


def test_end_auto_after_15_days(app, client, make):
    from app.models import Mentorship
    hs, hm, msid = _matched(client, make)
    client.post(f"/api/mentoring/{msid}/end", headers=hm)
    with app.app_context():
        ms = db.session.get(Mentorship, msid)
        ms.mentor_end_requested_at = utcnow() - timedelta(days=16)
        db.session.commit()
        from app.services.mentoring_service import auto_end_due
        assert auto_end_due() == 1


def test_mentoring_privacy(client, make):
    hs, hm, msid = _matched(client, make)
    _, other = make.student()
    assert client.post(f"/api/mentoring/{msid}/end", headers=login_as(client, other)).status_code == 404


# ---------------- C13 Notifications ----------------

def test_notifications_read_and_privacy(seeded):
    s1 = auth(seeded, "student@mentorconnect.demo")
    priya = auth(seeded, "mentor@mentorconnect.demo")
    mine = seeded.get("/api/notifications", headers=s1).get_json()
    theirs = seeded.get("/api/notifications", headers=priya).get_json()
    assert mine and theirs
    assert seeded.patch(f"/api/notifications/{theirs[0]['id']}/read", headers=s1).status_code == 404
    r = seeded.patch(f"/api/notifications/{mine[0]['id']}/read", headers=s1)
    assert r.status_code == 200 and r.get_json()["read"] is True
    seeded.patch("/api/notifications/read-all", headers=s1)
    assert all(n["read"] for n in seeded.get("/api/notifications", headers=s1).get_json())
