"""C1 Auth - US-01 (register and sign in with role-based access)."""

from tests.conftest import auth

STUDENT = {"email": "new.student@ds.study.iitm.ac.in", "password": "Secret123", "role": "student",
           "name": "New Student", "username": "new_student", "course": "data_science_and_applications",
           "courselevel": "bsc_degree", "interests": ["Data Science"]}
MENTOR = {"email": "alum@example.com", "password": "Secret123", "role": "mentor", "name": "New Mentor",
          "username": "new_mentor", "designation": "Analyst", "company": "Acme", "capacity": 2,
          "support_types": ["Resume review"], "expertise": ["Data Science"]}


def test_health(client):
    assert client.get("/api/health").get_json() == {"status": "ok"}


def test_student_registration_creates_profile_and_hides_password(seeded):
    r = seeded.post("/api/auth/register", json=STUDENT)
    assert r.status_code == 201
    body = r.get_json()
    assert body["role"] == "student" and body["student"]["course"] == "data_science_and_applications"
    assert [t["name"] for t in body["tags"]] == ["Data Science"]
    assert "password" not in body and "password" not in str(body)


def test_student_must_use_iitm_email(seeded):
    r = seeded.post("/api/auth/register", json={**STUDENT, "email": "someone@gmail.com"})
    assert r.status_code == 400
    assert "study.iitm.ac.in" in r.get_json()["error"]["message"]


def test_password_needs_letters_and_numbers(seeded):
    for bad in ["short1", "allletters", "12345678"]:
        r = seeded.post("/api/auth/register", json={**STUDENT, "password": bad})
        assert r.status_code == 400, bad


def test_duplicate_email_and_username(seeded):
    assert seeded.post("/api/auth/register", json=STUDENT).status_code == 201
    assert seeded.post("/api/auth/register", json={**STUDENT, "username": "other_one"}).status_code == 409
    assert seeded.post("/api/auth/register", json={**STUDENT, "email": "x@ds.study.iitm.ac.in"}).status_code == 409


def test_coordinator_and_admin_cannot_self_register(seeded):
    r = seeded.post("/api/auth/register", json={**STUDENT, "role": "admin"})
    assert r.status_code == 400


def test_mentor_registration_pending_and_admin_notified(seeded):
    r = seeded.post("/api/auth/register", json=MENTOR)
    assert r.status_code == 201
    m = r.get_json()["mentor"]
    assert m["veri_status"] == "pending" and m["pause"] is False and m["support_types"] == ["Resume review"]
    admin = auth(seeded, "admin@mentorconnect.demo")
    notes = seeded.get("/api/notifications", headers=admin).get_json()
    assert any("New Mentor" in n["message"] for n in notes)


def test_mentor_capacity_required_and_limited(seeded):
    no_cap = {k: v for k, v in MENTOR.items() if k != "capacity"}
    assert seeded.post("/api/auth/register", json=no_cap).status_code == 400
    assert seeded.post("/api/auth/register", json={**MENTOR, "capacity": 11}).status_code == 400
    assert seeded.post("/api/auth/register", json={**MENTOR, "capacity": 0}).status_code == 400


def test_unapproved_tag_rejected_at_registration(seeded):
    r = seeded.post("/api/auth/register", json={**STUDENT, "interests": ["UX Design"]})  # suggested, not approved
    assert r.status_code == 400


def test_login_success_and_me(seeded):
    h = auth(seeded, "student@mentorconnect.demo")
    me = seeded.get("/api/auth/me", headers=h).get_json()
    assert me["email"] == "student@mentorconnect.demo" and me["role"] == "student"


def test_login_accepts_form_fields_for_old_client(seeded):
    r = seeded.post("/api/auth/login", data={"username": "student@mentorconnect.demo", "password": "Demo1234"})
    assert r.status_code == 200 and r.get_json()["token_type"] == "bearer"


def test_wrong_password_and_unknown_email(seeded):
    assert seeded.post("/api/auth/login", json={"email": "student@mentorconnect.demo", "password": "nope1234"}).status_code == 401
    assert seeded.post("/api/auth/login", json={"email": "ghost@x.com", "password": "Demo1234"}).status_code == 401


def test_missing_and_invalid_token(seeded):
    assert seeded.get("/api/auth/me").status_code == 401
    assert seeded.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"}).status_code == 401


def test_expired_token_rejected(seeded_app):
    from app.security import create_access_token
    seeded_app.config["JWT_EXPIRE_MINUTES"] = -1
    with seeded_app.test_request_context():
        token, _ = create_access_token(1, "admin")
    r = seeded_app.test_client().get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401 and "expired" in r.get_json()["error"]["message"]


def test_blocked_user_cannot_log_in_or_use_token(seeded_app):
    from app.extensions import db
    from app.models import User, UserStatus
    c = seeded_app.test_client()
    h = auth(c, "student@mentorconnect.demo")
    with seeded_app.app_context():
        u = db.session.query(User).filter_by(email="student@mentorconnect.demo").one()
        u.status = UserStatus.deactive
        db.session.commit()
    assert c.post("/api/auth/login", json={"email": "student@mentorconnect.demo", "password": "Demo1234"}).status_code == 403
    assert c.get("/api/auth/me", headers=h).status_code == 401


def test_change_password(seeded):
    h = auth(seeded, "student@mentorconnect.demo")
    assert seeded.post("/api/auth/change-password", headers=h, json={"current_password": "wrong", "new_password": "NewPass123"}).status_code == 400
    assert seeded.post("/api/auth/change-password", headers=h, json={"current_password": "Demo1234", "new_password": "NewPass123"}).status_code == 200
    auth(seeded, "student@mentorconnect.demo", "NewPass123")
