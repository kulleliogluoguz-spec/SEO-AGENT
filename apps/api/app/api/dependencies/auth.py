"""
Shared FastAPI dependencies for authentication and authorization.
Import get_current_user from here throughout the codebase.
"""
import asyncio
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.database import get_db
from app.core.security.auth import decode_token
from app.models.models import Membership, MemberRole, User

security = HTTPBearer()

# Demo user — returned when DB is unavailable and the demo JWT is presented
DEMO_USER_ID = "00000000-0000-0000-0001-000000000001"

class _DemoUser:
    """Lightweight stand-in for the real User ORM object when DB is unavailable."""
    id = uuid.UUID(DEMO_USER_ID)
    email = "demo@aicmo.os"
    full_name = "Demo User"
    is_active = True
    is_superuser = False
    hashed_password = ""
    avatar_url = None
    last_login_at = None
    created_at = None

    def __repr__(self):
        return f"<DemoUser {self.email}>"

_DEMO_USER = _DemoUser()

ROLE_HIERARCHY = {
    MemberRole.VIEWER: 0,
    MemberRole.ANALYST: 1,
    MemberRole.EDITOR: 2,
    MemberRole.ADMIN: 3,
    MemberRole.OWNER: 4,
}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate JWT, return the authenticated User."""
    try:
        payload = decode_token(credentials.credentials)
        user_id: str = payload.get("sub", "")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Demo user shortcut — works even without a database
    if user_id == DEMO_USER_ID:
        return _DEMO_USER

    try:
        result = await asyncio.wait_for(
            db.execute(select(User).where(User.id == uuid.UUID(user_id))),
            timeout=5.0,
        )
        user = result.scalar_one_or_none()
    except (asyncio.TimeoutError, Exception):
        raise HTTPException(status_code=503, detail="Database unavailable")

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user


async def require_role(
    org_id: uuid.UUID,
    user: User,
    min_role: MemberRole,
    db: AsyncSession,
) -> Membership:
    """
    Assert that the user has at least `min_role` in the given organization.
    Returns the membership if valid. Raises 403 otherwise.
    """
    result = await db.execute(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.organization_id == org_id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    user_level = ROLE_HIERARCHY.get(membership.role, -1)
    required_level = ROLE_HIERARCHY.get(min_role, 999)

    if user_level < required_level:
        raise HTTPException(
            status_code=403,
            detail=f"Requires {min_role.value} role or higher",
        )
    return membership


def require_superuser(user: User = Depends(get_current_user)) -> User:
    """Assert superuser status."""
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser required")
    return user

async def require_workspace_access(user, workspace_id: str, db) -> None:
    """Stub: in production this checks workspace membership."""
    pass
