"""Shared pytest fixtures.

Every test gets a brand-new app with an in-memory SQLite database, so tests never
touch the real ``instance/mentorconnect.db`` and cannot affect each other.
"""

import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.models import Mentor, Student, User, UserRole, VerificationStatus
from app.security import hash_password

PASSWORD = "Passw0rd1"


@pytest.fixture
def app():
    app = create_app(TestConfig)
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def seeded_app():
    class SeededConfig(TestConfig):
        AUTO_SEED = True

    app = create_app(SeededConfig)
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seeded(seeded_app):
    return seeded_app.test_client()


def auth(client, email, password="Demo1234"):
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.get_json()
    return {"Authorization": f"Bearer {resp.get_json()['access_token']}"}


class Factory:
    """Creates users directly in the database (faster than going through the API)."""

    def __init__(self, app):
        self.app = app
        self.n = 0

    def _user(self, role, **extra):
        self.n += 1
        with self.app.app_context():
            u = User(name=extra.pop("name", f"{role.title()} {self.n}"),
                     email=extra.pop("email", f"{role}{self.n}@ds.study.iitm.ac.in"),
                     username=f"{role}_{self.n}", role=UserRole(role), password=hash_password(PASSWORD))
            if role == "student":
                u.student = Student()
            if role == "mentor":
                u.mentor = Mentor(designation="Engineer", company="Acme", capacity=extra.pop("capacity", 2),
                                  pause=extra.pop("pause", False),
                                  veri_status=extra.pop("veri", VerificationStatus.verified))
            db.session.add(u)
            db.session.commit()
            return u.id, u.email

    def student(self, **kw):
        uid, email = self._user("student", **kw)
        return uid, email

    def mentor(self, **kw):
        return self._user("mentor", **kw)

    def staff(self, role):
        return self._user(role)


@pytest.fixture
def make(app):
    return Factory(app)


def login_as(client, email):
    return auth(client, email, PASSWORD)


MSG = "I would really value your guidance on moving into a data science role while working full time."
