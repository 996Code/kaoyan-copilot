from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import (
    current_user, find_user, issue_token, register_user, seed_owner_if_empty, verify_password,
)
from app.core.db import get_session

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterIn(BaseModel):
    username: str = Field(min_length=2, max_length=32)
    password: str = Field(min_length=4, max_length=64)


class LoginIn(BaseModel):
    username: str
    password: str


def _auth_response(user) -> dict:
    return {
        "token": issue_token(user.id),
        "username": user.username,
        "is_admin": bool(user.is_admin),
    }


@router.post("/register")
def register(body: RegisterIn, session: Session = Depends(get_session)):
    if find_user(session, body.username) is not None:
        raise HTTPException(status_code=409, detail="用户名已存在")
    user = register_user(session, body.username, body.password)
    session.commit()
    return _auth_response(user)


@router.post("/login")
def login(body: LoginIn, session: Session = Depends(get_session)):
    seed_owner_if_empty(session)
    user = find_user(session, body.username)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return _auth_response(user)


@router.get("/me")
def me(user=Depends(current_user)):
    return {"id": user.id, "username": user.username, "is_admin": bool(user.is_admin)}
