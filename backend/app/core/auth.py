"""用户认证：PBKDF2 口令哈希 + HMAC 签名令牌（重启不失效，30 天有效期）。

令牌格式：{user_id}.{token_version}.{exp_unix}.{hmac_sha256(payload)}
- token_version 存于用户表，重置密码/删除用户时 +1，旧令牌即刻失效
- 签名密钥存 system_settings（首次自动生成）
"""

import hashlib
import hmac
import secrets
import time
from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_session

TOKEN_TTL = 30 * 86400  # 30 天


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


def _secret(session: Session) -> bytes:
    """签名密钥：存 system_settings，首次调用自动生成。"""
    from app.models.setting import SystemSetting

    row = session.get(SystemSetting, "token_secret")
    if row and row.value:
        return row.value.encode()
    secret = secrets.token_hex(32)
    session.add(SystemSetting(key="token_secret", value=secret))
    session.commit()
    return secret.encode()


def issue_token(user_id: int, token_version: int = 0) -> str:
    payload = f"{user_id}.{token_version}.{int(time.time()) + TOKEN_TTL}"
    sig = hmac.new(settings.token_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def verify_token(token: str, token_version: int = 0) -> int | None:
    """校验签名与有效期，返回 user_id；无效返回 None。"""
    try:
        payload, sig = token.rsplit(".", 1)
        user_id, version, exp = payload.split(".")
        if int(version) != token_version or int(exp) < time.time():
            return None
        expect = hmac.new(settings.token_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not secrets.compare_digest(sig, expect):
            return None
        return int(user_id)
    except (ValueError, AttributeError):
        return None


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
    from app.models.user import User

    user_id = verify_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


def require_admin(user=Depends(current_user)) -> "User":
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user
