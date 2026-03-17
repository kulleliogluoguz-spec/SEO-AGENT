"""
Shared FastAPI dependencies for authentication and authorization.
Import get_current_user from here throughout the codebase.
"""
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

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
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
