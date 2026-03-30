"""
Authentication endpoints: login, register, refresh, me.

IMPORTANT: get_current_user dependency is imported from app.api.dependencies.auth
and NOT redefined here. The original code defined it after use (NameError at import).
"""
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.config.settings import get_settings
from app.core.db.database import get_db
from app.core.security.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.models import MemberRole, Membership, Organization, User, Workspace
from app.schemas.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse

router = APIRouter()
settings = get_settings()


DEMO_USER_ID = "00000000-0000-0000-0001-000000000001"


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate with email+password, return JWT tokens.

    Demo shortcut: if the DB is unavailable, demo@aicmo.os / Demo1234! still works.
    """
    email = payload.email.lower()

    # ── Demo shortcut (works even without a DB) ───────────────────────────────
    if email == settings.demo_user_email and payload.password == settings.demo_user_password:
        return TokenResponse(
            access_token=create_access_token(DEMO_USER_ID),
            refresh_token=create_refresh_token(DEMO_USER_ID),
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )

    # ── Normal DB path ────────────────────────────────────────────────────────
    try:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable. Use demo@aicmo.os / Demo1234! for demo access.",
        )

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Register new user and auto-create personal org + workspace."""
    existing = await db.execute(select(User).where(User.email == payload.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    await db.flush()

    base_slug = re.sub(r"[^a-z0-9]+", "-", payload.full_name.lower()).strip("-")[:40]
    org_slug = f"{base_slug}-{str(user.id)[:8]}"
    org = Organization(name=f"{payload.full_name}'s Organization", slug=org_slug)
    db.add(org)
    await db.flush()

    db.add(Membership(
        user_id=user.id, organization_id=org.id,
        role=MemberRole.OWNER, accepted_at=datetime.now(timezone.utc),
    ))
    db.add(Workspace(organization_id=org.id, name="My Workspace", slug="my-workspace", autonomy_level=1))
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token_endpoint(
    refresh_token: str,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Exchange refresh token for new access token."""
    from jose import JWTError
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return authenticated user profile including their first workspace ID."""
    # Resolve the user's first workspace via their org membership.
    # Gracefully handles DB unavailability (returns workspace_id=None).
    workspace_id = None
    if str(current_user.id) != DEMO_USER_ID:
        try:
            result = await db.execute(
                select(Workspace)
                .join(Organization, Workspace.organization_id == Organization.id)
                .join(Membership, Membership.organization_id == Organization.id)
                .where(Membership.user_id == current_user.id)
                .limit(1)
            )
            workspace = result.scalar_one_or_none()
            if workspace:
                workspace_id = workspace.id
        except Exception:
            pass  # DB unavailable — workspace_id stays None

    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "avatar_url": current_user.avatar_url,
        "is_active": current_user.is_active,
        "created_at": getattr(current_user, "created_at", None) or datetime.now(timezone.utc),
        "workspace_id": workspace_id,
    }
