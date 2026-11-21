"""Small helpers shared by routes and services."""

from datetime import datetime

from flask import request
from pydantic import BaseModel

from app.errors import BadRequest


def iso(value: datetime | None) -> str | None:
    """Serialise a stored (naive UTC) datetime as ISO-8601 with a 'Z' so browsers read it as UTC."""
    return value.isoformat(timespec="seconds") + "Z" if value else None


def parse_body(schema: type[BaseModel]) -> BaseModel:
    """Validate the JSON body against a Pydantic schema (route layer: 'validate shape')."""
    data = request.get_json(silent=True)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise BadRequest("Request body must be a JSON object.")
    return schema.model_validate(data)


def query_bool(name: str) -> bool | None:
    value = request.args.get(name)
    if value is None or value == "":
        return None
    return value.lower() in ("1", "true", "yes", "on")


def query_int(name: str, default: int, minimum: int = 1, maximum: int = 1000) -> int:
    try:
        value = int(request.args.get(name, default))
    except (TypeError, ValueError):
        raise BadRequest(f"{name} must be a whole number.")
    return max(minimum, min(maximum, value))
