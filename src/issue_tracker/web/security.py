from __future__ import annotations

from collections import defaultdict

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from issue_tracker.services.tracker import AuthService

ph = PasswordHasher()
_login_attempts: dict[str, int] = defaultdict(int)


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def note_failed_login(username: str) -> None:
    _login_attempts[username] += 1


def clear_failed_login(username: str) -> None:
    _login_attempts.pop(username, None)


def login_limited(username: str) -> bool:
    return _login_attempts[username] >= 5


def require_user(request: Request, session: Session) -> str:
    username = request.session.get("username")
    if not username:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    if AuthService(session).get_user(username) is None:
        request.session.clear()
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    return username
