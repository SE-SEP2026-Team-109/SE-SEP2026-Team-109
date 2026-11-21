"""Application configuration.

Values come from environment variables (or a local ``.env`` file) so secrets are
never hard-coded. Every business limit from the Milestone 2 "Validators and
config" mechanism lives here in one place, so a rule change is a one-line edit.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{(BASE_DIR / 'instance' / 'mentorconnect.db').as_posix()}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "120"))  # M1 5.1: 120-minute expiry
    CORS_ORIGINS = _list(os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"))
    # Seed demo data automatically the first time the app starts with an empty database.
    AUTO_SEED = os.getenv("AUTO_SEED", "1") == "1"

    # ---- Business limits (M1 user stories, M2 "Validators and config") ----
    REQUEST_EXPIRY_DAYS = 14          # US-06 / US-09
    MAX_PENDING_REQUESTS = 3          # US-06
    REQUEST_MESSAGE_MIN = 50          # US-06
    REQUEST_MESSAGE_MAX = 1500        # US-06
    REJECT_REASON_MAX = 500           # US-08
    STUDENT_MAX_TAGS = 5              # US-02
    MENTOR_MAX_TAGS = 6               # US-03
    CAPACITY_MIN = 1                  # US-03 / US-04 acceptance criteria
    CAPACITY_MAX = 10
    MENTORSHIP_END_RESPONSE_DAYS = 15  # M2 C6
    STUDENT_EMAIL_DOMAIN = "study.iitm.ac.in"  # US-01
    PHOTO_MAX_CHARS = 400_000         # data-URL photos (frontend resizes to 200px)


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    AUTO_SEED = False
    SECRET_KEY = "test-secret-key-that-is-long-enough-for-hs256"
