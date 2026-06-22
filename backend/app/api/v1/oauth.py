"""OAuth endpoints for GitHub and Google login."""

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember

router = APIRouter()
settings = get_settings()


class OAuthCallbackRequest(BaseModel):
    code: str


class OAuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    is_new_user: bool = False


# ─── GitHub OAuth ──────────────────────────────────────────────────


@router.get("/github/authorize")
async def github_authorize_url():
    """Get the GitHub OAuth authorization URL."""
    if not settings.github_client_id:
        raise HTTPException(status_code=501, detail="GitHub OAuth not configured")
    # Redirect URI is configurable for different deployment environments
    redirect_uri = f"{settings.oauth_redirect_base_url}/auth/github/callback"
    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.github_client_id}"
        f"&scope=user:email"
        f"&response_type=code"
        f"&redirect_uri={redirect_uri}"
    )
    return {"url": url}


@router.post("/github/callback", response_model=OAuthTokenResponse)
async def github_callback(body: OAuthCallbackRequest, db: AsyncSession = Depends(get_db)):
    """Exchange GitHub authorization code for user info and create/login user."""
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(status_code=501, detail="GitHub OAuth not configured")

    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": body.code,
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_resp.json()

    if "error" in token_data:
        raise HTTPException(status_code=400, detail=token_data.get("error_description", "OAuth failed"))

    github_token = token_data.get("access_token")
    if not github_token:
        raise HTTPException(status_code=400, detail="No access token received")

    # Fetch user info
    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {github_token}"},
        )
        github_user = user_resp.json()

    oauth_id = str(github_user.get("id"))
    email = github_user.get("email") or f"{github_user.get('login')}@github.oauth"
    full_name = github_user.get("name") or github_user.get("login")

    return await _find_or_create_oauth_user(db, "github", oauth_id, email, full_name)


# ─── Google OAuth ──────────────────────────────────────────────────


@router.get("/google/authorize")
async def google_authorize_url():
    """Get the Google OAuth authorization URL."""
    if not settings.google_client_id:
        raise HTTPException(status_code=501, detail="Google OAuth not configured")
    # Use postmessage for client-side OAuth flow, or configure redirect_uri for server-side
    redirect_uri = f"{settings.oauth_redirect_base_url}/auth/google/callback"
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.google_client_id}"
        f"&scope=openid%20email%20profile"
        f"&response_type=code"
        f"&redirect_uri={redirect_uri}"
    )
    return {"url": url}


@router.post("/google/callback", response_model=OAuthTokenResponse)
async def google_callback(body: OAuthCallbackRequest, db: AsyncSession = Depends(get_db)):
    """Exchange Google authorization code for user info and create/login user."""
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=501, detail="Google OAuth not configured")

    # Exchange code for tokens
    redirect_uri = f"{settings.oauth_redirect_base_url}/auth/google/callback"
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            json={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "code": body.code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )
        token_data = token_resp.json()

    if "error" in token_data:
        raise HTTPException(status_code=400, detail=token_data.get("error_description", "OAuth failed"))

    google_token = token_data.get("access_token") or token_data.get("id_token")
    if not google_token:
        raise HTTPException(status_code=400, detail="No access token received")

    # Fetch user info
    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {google_token}"},
        )
        google_user = user_resp.json()

    oauth_id = str(google_user.get("id"))
    email = google_user.get("email", f"{oauth_id}@google.oauth")
    full_name = google_user.get("name") or email.split("@")[0]

    return await _find_or_create_oauth_user(db, "google", oauth_id, email, full_name)


# ─── Shared helper ─────────────────────────────────────────────────


async def _find_or_create_oauth_user(
    db: AsyncSession,
    provider: str,
    oauth_id: str,
    email: str,
    full_name: str,
) -> OAuthTokenResponse:
    """Find existing user by OAuth ID or email, or create a new one."""
    is_new = False

    # Try to find by OAuth ID
    result = await db.execute(
        select(User).where(User.oauth_provider == provider, User.oauth_id == oauth_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        # Try to find by email
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

    if not user:
        # Create new user
        user = User(
            email=email,
            full_name=full_name,
            oauth_provider=provider,
            oauth_id=oauth_id,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)

        # Create default workspace
        workspace = Workspace(name="My Workspace", owner_id=user.id)
        db.add(workspace)
        await db.flush()
        member = WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="owner")
        db.add(member)
        await db.flush()
        is_new = True
    elif not user.oauth_id:
        # Link OAuth to existing email user
        user.oauth_provider = provider
        user.oauth_id = oauth_id
        await db.flush()

    token_data = {"sub": user.id, "email": user.email}
    return OAuthTokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        is_new_user=is_new,
    )
