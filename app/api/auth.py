"""Invite-code signup + JWT login, and the protected-route dependency.

Closes AC0.9. The JWT/password primitives live in `app/users/auth.py` (framework
-free); this module is the FastAPI surface over them.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import AfterValidator, BaseModel, Field, StringConstraints
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.db.session import get_session
from app.users.auth import create_token, hash_password, verify_password, verify_token
from app.users.models import User

router = APIRouter(prefix="/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=False)

# Normalize once so signup and login key on the same value — otherwise `Bob@x.com` and
# `bob@x.com` become two accounts and login can't find a differently-cased signup (qa-101).
NormalizedEmail = Annotated[str, AfterValidator(lambda v: v.strip().lower())]


class SignupRequest(BaseModel):
    email: NormalizedEmail
    password: str = Field(min_length=8)
    invite_code: str
    # required, non-blank, and capped: a blank name falls back to email on the shared
    # board (qa-010); an unbounded one floods every board response / breaks the UI (qa-130)
    display_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)
    ]


class LoginRequest(BaseModel):
    email: NormalizedEmail
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    display_name: str


async def _user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    body: SignupRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    if body.invite_code not in settings.invite_code_set:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "invalid invite code")
    user = User(
        email=body.email,
        display_name=body.display_name,
        password_hash=hash_password(body.password),
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "email already registered") from None
    await session.refresh(user)
    return TokenResponse(
        access_token=create_token(subject=str(user.id), secret=settings.jwt_secret)
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    user = await _user_by_email(session, body.email)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    return TokenResponse(
        access_token=create_token(subject=str(user.id), secret=settings.jwt_secret)
    )


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    try:
        payload = verify_token(creds.credentials, settings.jwt_secret)
    except Exception:  # noqa: BLE001 - any JWT failure is an auth failure
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or expired token") from None
    user = await session.get(User, int(payload["sub"]))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user not found")
    return user


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(id=user.id, email=user.email, display_name=user.display_name)
