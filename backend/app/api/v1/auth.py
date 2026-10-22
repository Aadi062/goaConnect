"""Authentication routes: register, login, refresh, logout, whoami."""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.core.deps import get_current_user
from app.db.models.user import User
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, UserOut, RefreshRequest
from app.services.security.audit import log_event
from app.core.config import get_settings
from jose import JWTError

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, request: Request, db: AsyncSession = Depends(get_db)):
    # Check email/username uniqueness
    existing = await db.execute(
        select(User).where((User.email == data.email) | (User.username == data.username))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already registered",
        )

    user = User(
        id=str(uuid.uuid4()),
        email=data.email,
        username=data.username,
        hashed_password=hash_password(data.password),
        role="viewer",
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    await db.flush()

    await log_event(
        db,
        event_type="auth.register",
        action="register",
        outcome="success",
        user_id=user.id,
        username=user.username,
        ip_address=request.client.host if request.client else None,
    )
    return user


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()
    ip = request.client.host if request.client else None

    if not user or not user.is_active:
        await log_event(
            db, "auth.login", "login", "failure",
            username=data.username, ip_address=ip,
            detail={"reason": "user_not_found_or_inactive"},
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Lockout check
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        await log_event(
            db, "auth.login", "login", "blocked",
            user_id=user.id, username=user.username, ip_address=ip,
            detail={"reason": "account_locked"},
        )
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account temporarily locked due to failed attempts",
        )

    if not verify_password(data.password, user.hashed_password):
        user.failed_login_count += 1
        if user.failed_login_count >= MAX_FAILED_ATTEMPTS:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
        await log_event(
            db, "auth.login", "login", "failure",
            user_id=user.id, username=user.username, ip_address=ip,
            detail={"failed_count": user.failed_login_count},
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Success — reset counters
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login = datetime.now(timezone.utc)

    access_token = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id)

    await log_event(
        db, "auth.login", "login", "success",
        user_id=user.id, username=user.username, ip_address=ip,
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(data.refresh_token)
        if payload.get("type") != "refresh":
            raise JWTError("Not a refresh token")
        user_id = payload["sub"]
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive")

    access_token = create_access_token(user.id, user.role)
    new_refresh = create_refresh_token(user.id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserOut)
async def whoami(current_user: User = Depends(get_current_user)):
    return current_user
