from app.models.enums import StudentType, VerificationStatus
from app.models.user import Mentor, Student


def test_register_creates_user(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "student@study.iitm.ac.in",
            "password": "password123",
            "role": "student",
            "course": "data_science_and_applications",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "student@study.iitm.ac.in"
    assert body["role"] == "student"
    assert "password" not in body


def test_register_rejects_duplicate_email(client):
    payload = {
        "email": "dup@study.iitm.ac.in",
        "password": "password123",
        "role": "student",
        "course": "data_science_and_applications",
    }
    client.post("/api/auth/register", json=payload)
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 400


def test_register_rejects_duplicate_username(client):
    payload = {
        "email": "user1@study.iitm.ac.in",
        "password": "password123",
        "role": "student",
        "course": "data_science_and_applications",
        "username": "sameuser",
    }
    client.post("/api/auth/register", json=payload)
    response = client.post(
        "/api/auth/register",
        json={**payload, "email": "user2@study.iitm.ac.in"},
    )
    assert response.status_code == 400


def test_register_requires_course_for_student(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "nocourse@study.iitm.ac.in", "password": "password123", "role": "student"},
    )
    assert response.status_code == 400
    assert "Course is required" in response.json()["detail"]


def test_register_rejects_invalid_course_enum(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "badcourse@study.iitm.ac.in",
            "password": "password123",
            "role": "student",
            "course": "DS",
        },
    )
    assert response.status_code == 422


def test_register_creates_student_row_with_submitted_fields(client, db_session):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "fulldetails@study.iitm.ac.in",
            "password": "password123",
            "role": "student",
            "course": "electronic_systems",
            "courselevel": "bs_degree",
            "student_type": "dual_degree",
            "rollno": "24f1002112",
            "careergoal": "Become a data engineer",
        },
    )
    assert response.status_code == 201
    user_id = response.json()["id"]

    student = db_session.get(Student, user_id)
    assert student is not None
    assert student.course.value == "electronic_systems"
    assert student.courselevel.value == "bs_degree"
    assert student.type == StudentType.dual_degree
    assert student.rollno == "24f1002112"
    assert student.careergoal == "Become a data engineer"


def test_register_student_type_defaults_to_standalone(client, db_session):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "defaulttype@study.iitm.ac.in",
            "password": "password123",
            "role": "student",
            "course": "aeronautics_and_space_technology",
        },
    )
    assert response.status_code == 201
    student = db_session.get(Student, response.json()["id"])
    assert student.type == StudentType.standalone


def test_register_requires_capacity_for_mentor(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "nocapacity@mentorconnect.in", "password": "password123", "role": "mentor"},
    )
    assert response.status_code == 400
    assert "Capacity is required" in response.json()["detail"]


def test_register_creates_mentor_row_with_submitted_fields(client, db_session):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "mentorfull@mentorconnect.in",
            "password": "password123",
            "role": "mentor",
            "capacity": 5,
            "designation": "Senior Engineer",
            "company": "Acme Corp",
            "experience": 7.5,
            "bio": "Happy to help with careers in data.",
            "level_completed": "bs_degree",
            "year_completed": 2019,
        },
    )
    assert response.status_code == 201
    user_id = response.json()["id"]

    mentor = db_session.get(Mentor, user_id)
    assert mentor is not None
    assert mentor.capacity == 5
    assert mentor.designation == "Senior Engineer"
    assert mentor.company == "Acme Corp"
    assert mentor.experience == 7.5
    assert mentor.level_completed.value == "bs_degree"
    assert mentor.year_completed == 2019


def test_register_mentor_defaults_to_pending_verification_and_not_paused(client, db_session):
    response = client.post(
        "/api/auth/register",
        json={"email": "pendingmentor@mentorconnect.in", "password": "password123", "role": "mentor", "capacity": 2},
    )
    assert response.status_code == 201
    mentor = db_session.get(Mentor, response.json()["id"])
    assert mentor.veri_status == VerificationStatus.pending
    assert mentor.pause is False


def test_login_returns_token_for_valid_credentials(client):
    client.post(
        "/api/auth/register",
        json={"email": "mentor@mentorconnect.in", "password": "password123", "role": "mentor", "capacity": 3},
    )
    response = client.post(
        "/api/auth/login",
        data={"username": "mentor@mentorconnect.in", "password": "password123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_rejects_wrong_password(client):
    client.post(
        "/api/auth/register",
        json={
            "email": "wrongpw@study.iitm.ac.in",
            "password": "password123",
            "role": "student",
            "course": "data_science_and_applications",
        },
    )
    response = client.post(
        "/api/auth/login",
        data={"username": "wrongpw@study.iitm.ac.in", "password": "nope"},
    )
    assert response.status_code == 401


def test_me_requires_valid_token(client):
    register = client.post(
        "/api/auth/register",
        json={
            "email": "me@study.iitm.ac.in",
            "password": "password123",
            "role": "student",
            "course": "data_science_and_applications",
        },
    )
    assert register.status_code == 201

    login = client.post(
        "/api/auth/login",
        data={"username": "me@study.iitm.ac.in", "password": "password123"},
    )
    token = login.json()["access_token"]

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "me@study.iitm.ac.in"


def test_me_rejects_missing_token(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401
