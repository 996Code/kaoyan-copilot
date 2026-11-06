"""用户认证：PBKDF2 口令哈希 + 内存 token（token -> user_id，重启失效）。"""

import hashlib
import secrets
from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_session

if TYPE_CHECKING:
    from app.models.user import User

_tokens: dict[str, int] = {}  # token -> user_id


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000)
    return f"pbkdf2_sha256$260000${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _algo, iters, salt, expected = stored.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iters))
        return secrets.compare_digest(digest.hex(), expected)
    except (ValueError, AttributeError):
        return False


def issue_token(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    _tokens[token] = user_id
    return token


def find_user(session: Session, username: str) -> "User | None":
    from app.models.user import User

    return session.scalar(select(User).where(User.username == username))


def register_user(session: Session, username: str, password: str) -> "User":
    from app.models.user import User

    user = User(username=username, password_hash=hash_password(password))
    session.add(user)
    session.flush()
    return user


def seed_owner_if_empty(session: Session) -> None:
    """无任何用户时，用 .env 的 AUTH_USERNAME/AUTH_PASSWORD 建立首个管理员账号。"""
    from app.models.user import User

    if session.scalar(select(User).limit(1)) is None:
        user = register_user(session, settings.auth_username, settings.auth_password)
        user.is_admin = True
        session.commit()
        print(f"[auth] 已创建初始管理员 {settings.auth_username!r}")


def current_user(request: Request, session: Session = Depends(get_session)) -> "User":
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = auth.removeprefix("Bearer ").strip()
    user_id = _tokens.get(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")
    from app.models.user import User

    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


def require_admin(user=Depends(current_user)) -> "User":
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user
