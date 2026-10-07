"""
NIA Backend — /api/v1/auth
JWT authentication: register, login, refresh, logout.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, field_validator

from ...core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
    sanitize_user_input,
)

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# ── In-memory user store (swap for real DB in production) ──────────────────
_users: dict[str, dict] = {}          # { user_id: user_record }
_email_index: dict[str, str] = {}     # { email: user_id }
_refresh_tokens: dict[str, str] = {}  # { jti: user_id }


# ── Schemas ────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v

    @field_validator("display_name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        return sanitize_user_input(v)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    created_at: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Helpers ────────────────────────────────────────────────────────────────

def _get_user_by_id(user_id: str) -> Optional[dict]:
    return _users.get(user_id)


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> dict:
    """Dependency: decodes bearer token and returns the user record."""
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise ValueError("Not an access token.")
        user_id: str = payload["sub"]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    user = _get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    return user


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest):
    if req.email in _email_index:
        raise HTTPException(status_code=400, detail="Email already registered.")
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    user = {
        "id": user_id,
        "email": req.email,
        "display_name": req.display_name,
        "password_hash": hash_password(req.password),
        "created_at": now,
    }
    _users[user_id] = user
    _email_index[req.email] = user_id
    return UserResponse(id=user_id, email=req.email, display_name=req.display_name, created_at=now)


@router.post("/login", response_model=TokenResponse)
async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user_id = _email_index.get(form.username)
    user = _users.get(user_id) if user_id else None
    if user is None or not verify_password(form.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    access_token = create_access_token(user["id"])
    refresh_token = create_refresh_token(user["id"])
    # Store jti for revocation support
    payload = decode_token(refresh_token)
    _refresh_tokens[payload["jti"]] = user["id"]
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshRequest):
    try:
        payload = decode_token(req.refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError("Not a refresh token.")
        jti = payload["jti"]
        user_id = payload["sub"]
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh token.") from exc
    if _refresh_tokens.get(jti) != user_id:
        raise HTTPException(status_code=401, detail="Refresh token revoked or not found.")
    # Rotate: revoke old, issue new
    del _refresh_tokens[jti]
    new_access = create_access_token(user_id)
    new_refresh = create_refresh_token(user_id)
    new_payload = decode_token(new_refresh)
    _refresh_tokens[new_payload["jti"]] = user_id
    return TokenResponse(access_token=new_access, refresh_token=new_refresh)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(req: RefreshRequest):
    try:
        payload = decode_token(req.refresh_token)
        jti = payload.get("jti", "")
        _refresh_tokens.pop(jti, None)
    except Exception:
        pass  # Always succeed on logout


@router.get("/me", response_model=UserResponse)
async def me(current_user: Annotated[dict, Depends(get_current_user)]):
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        display_name=current_user["display_name"],
        created_at=current_user["created_at"],
    )
