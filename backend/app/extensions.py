"""Shared Flask extensions, created once and initialised inside ``create_app``."""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all models (SQLAlchemy 2.0 typed style, same as the FastAPI code)."""


db = SQLAlchemy(model_class=Base)
