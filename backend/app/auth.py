"""Username + password, JWT in an HttpOnly cookie. Accounts are created by the admin (cli.py)."""
from __future__ import annotations

from datetime import timedelta

import bcrypt
import jwt
from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session, utcnow
from app.models import User

COOKIE = "sponsr_session"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def issue_token(user: User) -> str:
    s = get_settings()
    claims = {"sub": str(user.id), "exp": utcnow() + timedelta(days=s.session_days)}
    return jwt.encode(claims, s.jwt_secret.get_secret_value(), algorithm="HS256")


def current_user(sponsr_session: str | None = Cookie(default=None), session: Session = Depends(get_session)) -> User:
    if not sponsr_session:
        raise HTTPException(401, "sign in")
    try:
        claims = jwt.decode(sponsr_session, get_settings().jwt_secret.get_secret_value(), algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "session expired; sign in again") from None
    user = session.get(User, int(claims["sub"]))
    if user is None:
        raise HTTPException(401, "sign in")
    return user
