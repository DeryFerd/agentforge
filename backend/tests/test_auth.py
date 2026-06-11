"""Tests for authentication endpoints and RBAC dependencies."""

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, hash_password


@pytest.mark.asyncio
class TestRegister:
    """Test user registration endpoint."""

    async def test_register_success(self, client: AsyncClient):
        """Should create a new user and return 201."""
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com", "password": "strongpass123", "full_name": "Test User"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"
        assert "id" in data

    async def test_register_duplicate_email(self, client: AsyncClient):
        """Should reject duplicate email with 409."""
        payload = {"email": "dupe@example.com", "password": "strongpass123", "full_name": "User"}
        await client.post("/api/v1/auth/register", json=payload)
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 409
        assert "already registered" in response.json()["detail"].lower()

    async def test_register_invalid_email(self, client: AsyncClient):
        """Should reject invalid email format."""
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "strongpass123", "full_name": "Test"},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestLogin:
    """Test login endpoint."""

    async def test_login_success(self, client: AsyncClient):
        """Should return access and refresh tokens."""
        # Register first
        await client.post(
            "/api/v1/auth/register",
            json={"email": "login@example.com", "password": "strongpass123", "full_name": "Login User"},
        )
        # Login
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "login@example.com", "password": "strongpass123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient):
        """Should return 401 for wrong password."""
        await client.post(
            "/api/v1/auth/register",
            json={"email": "wrong@example.com", "password": "correct", "full_name": "User"},
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "wrong@example.com", "password": "incorrect"},
        )
        assert response.status_code == 401

    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Should return 401 for non-existent user."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "anything"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
class TestGetMe:
    """Test the /me endpoint with JWT auth."""

    async def test_get_me_authenticated(self, client: AsyncClient):
        """Should return user profile with valid token."""
        # Register + Login
        await client.post(
            "/api/v1/auth/register",
            json={"email": "me@example.com", "password": "pass123", "full_name": "Me User"},
        )
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "me@example.com", "password": "pass123"},
        )
        token = login_resp.json()["access_token"]

        # Get /me
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["email"] == "me@example.com"

    async def test_get_me_no_token(self, client: AsyncClient):
        """Should return 422 without Authorization header."""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 422

    async def test_get_me_invalid_token(self, client: AsyncClient):
        """Should return 401 with invalid token."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token-here"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
class TestRefreshToken:
    """Test token refresh endpoint."""

    async def test_refresh_success(self, client: AsyncClient):
        """Should return new tokens with valid refresh token."""
        await client.post(
            "/api/v1/auth/register",
            json={"email": "refresh@example.com", "password": "pass123", "full_name": "User"},
        )
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "refresh@example.com", "password": "pass123"},
        )
        refresh_token = login_resp.json()["refresh_token"]

        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_refresh_with_access_token(self, client: AsyncClient):
        """Should reject access token used as refresh token."""
        await client.post(
            "/api/v1/auth/register",
            json={"email": "nope@example.com", "password": "pass123", "full_name": "User"},
        )
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "nope@example.com", "password": "pass123"},
        )
        access_token = login_resp.json()["access_token"]

        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
class TestHealthCheck:
    """Test health check endpoint."""

    async def test_health(self, client: AsyncClient):
        """Should return healthy status."""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
