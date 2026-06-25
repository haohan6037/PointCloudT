from datetime import datetime
from hashlib import sha256
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.entities import AuthSession, Device, User


def get_user_from_bearer(authorization: Optional[str], db: Session) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    token_hash = sha256(token.encode()).hexdigest()
    session = (
        db.query(AuthSession)
        .filter(AuthSession.token_hash == token_hash, AuthSession.expires_at > datetime.utcnow())
        .first()
    )
    if not session:
        raise HTTPException(401, "Invalid or expired session")
    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(401, "User not found")
    return user


def device_for_user(db: Session, user: User, device_id: int) -> Device:
    device = db.get(Device, device_id)
    if not device or device.owner_id != user.id:
        raise HTTPException(404, "Device not found")
    return device


def validate_time_hhmm(value: str, field_name: str) -> str:
    parts = value.split(":")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        raise HTTPException(400, f"{field_name} must use HH:MM format")
    hour = int(parts[0])
    minute = int(parts[1])
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise HTTPException(400, f"{field_name} must be a valid time")
    return f"{hour:02d}:{minute:02d}"
