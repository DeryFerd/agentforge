"""Shared FastAPI dependencies for authentication, authorization, and audit logging."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.misc import AuditLog
from app.models.user import User
from app.models.workspace import WorkspaceMember


# ─── Auth Dependencies ────────────────────────────────────────────


async def get_current_user(
    authorization: str | None = Header(None, description="Bearer <token>"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate JWT and return the authenticated User object.

    Raises 401 if the token is missing, invalid, or the user doesn't exist.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must start with 'Bearer '",
        )

    token = authorization.removeprefix("Bearer ")
    payload = decode_token(token)

    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is not an access token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing 'sub' claim")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated")

    return user


async def get_current_user_id(
    user: Annotated[User, Depends(get_current_user)],
) -> str:
    """Convenience: extract just the user ID from the authenticated user."""
    return user.id


# ─── RBAC Dependencies ────────────────────────────────────────────


# Role hierarchy: owner > admin > editor > viewer
ROLE_HIERARCHY = {
    "owner": 4,
    "admin": 3,
    "editor": 2,
    "viewer": 1,
}


class RequireRole:
    """Dependency factory: requires the user to have at least `min_role` in a workspace.

    Usage in endpoint:
        @router.post("/workflows")
        async def create_workflow(
            workspace_id: str,
            user: User = Depends(get_current_user),
            _: None = Depends(RequireRole("editor")),
            db: AsyncSession = Depends(get_db),
        ):
    """

    def __init__(self, min_role: str):
        self.min_role = min_role
        self.min_level = ROLE_HIERARCHY.get(min_role, 0)

    async def __call__(
        self,
        workspace_id: str,
        user: Annotated[User, Depends(get_current_user)],
        db: AsyncSession = Depends(get_db),
    ) -> WorkspaceMember:
        result = await db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user.id,
            )
        )
        member = result.scalar_one_or_none()

        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this workspace",
            )

        member_level = ROLE_HIERARCHY.get(member.role, 0)
        if member_level < self.min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires at least '{self.min_role}' role. You have '{member.role}'.",
            )

        return member


# Pre-built dependency instances for convenience
require_owner = RequireRole("owner")
require_admin = RequireRole("admin")
require_editor = RequireRole("editor")
require_viewer = RequireRole("viewer")


# ─── Audit Logging ────────────────────────────────────────────────


async def log_audit(
    db: AsyncSession,
    workspace_id: str,
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    details: dict | None = None,
) -> None:
    """Write an audit log entry. Call this from service/endpoint code."""
    entry = AuditLog(
        workspace_id=workspace_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details_json=details,
    )
    db.add(entry)
    await db.flush()
