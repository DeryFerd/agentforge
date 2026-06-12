"""Integration tests for workflow CRUD endpoints."""

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, hash_password


async def _register_and_get_token(client: AsyncClient) -> str:
    """Helper: register a user and return a JWT access token."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "wf_test@example.com", "password": "testpass123", "full_name": "WF Tester"},
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "wf_test@example.com", "password": "testpass123"},
    )
    return login_resp.json()["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
class TestWorkflowCRUD:
    """Test workflow create, read, update, delete endpoints."""

    async def test_create_workflow(self, client: AsyncClient):
        token = await _register_and_get_token(client)

        response = await client.post(
            "/api/v1/workflows",
            json={
                "workspace_id": "test-ws",
                "name": "Test Workflow",
                "description": "A test workflow",
                "dag_json": {"nodes": [], "edges": []},
            },
            headers=_headers(token),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Workflow"
        assert data["version"] == 1
        assert data["is_active"] is True

    async def test_list_workflows(self, client: AsyncClient):
        token = await _register_and_get_token(client)

        # Create a workflow first
        await client.post(
            "/api/v1/workflows",
            json={"workspace_id": "test-ws", "name": "List Test"},
            headers=_headers(token),
        )

        response = await client.get("/api/v1/workflows", headers=_headers(token))
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    async def test_get_workflow(self, client: AsyncClient):
        token = await _register_and_get_token(client)

        create_resp = await client.post(
            "/api/v1/workflows",
            json={"workspace_id": "test-ws", "name": "Get Test"},
            headers=_headers(token),
        )
        wf_id = create_resp.json()["id"]

        response = await client.get(f"/api/v1/workflows/{wf_id}", headers=_headers(token))
        assert response.status_code == 200
        assert response.json()["name"] == "Get Test"

    async def test_get_nonexistent_workflow(self, client: AsyncClient):
        token = await _register_and_get_token(client)

        response = await client.get(
            "/api/v1/workflows/nonexistent-id",
            headers=_headers(token),
        )
        assert response.status_code == 404

    async def test_update_workflow(self, client: AsyncClient):
        token = await _register_and_get_token(client)

        create_resp = await client.post(
            "/api/v1/workflows",
            json={"workspace_id": "test-ws", "name": "Update Test"},
            headers=_headers(token),
        )
        wf_id = create_resp.json()["id"]

        response = await client.put(
            f"/api/v1/workflows/{wf_id}",
            json={
                "name": "Updated Name",
                "dag_json": {"nodes": [{"id": "n1", "type": "agent"}], "edges": []},
            },
            headers=_headers(token),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["version"] == 2  # Version incremented

    async def test_delete_workflow(self, client: AsyncClient):
        token = await _register_and_get_token(client)

        create_resp = await client.post(
            "/api/v1/workflows",
            json={"workspace_id": "test-ws", "name": "Delete Test"},
            headers=_headers(token),
        )
        wf_id = create_resp.json()["id"]

        response = await client.delete(
            f"/api/v1/workflows/{wf_id}",
            headers=_headers(token),
        )
        assert response.status_code == 204

        # Should not appear in active list
        list_resp = await client.get("/api/v1/workflows", headers=_headers(token))
        ids = [w["id"] for w in list_resp.json()]
        assert wf_id not in ids


@pytest.mark.asyncio
class TestWorkflowValidation:
    """Test the workflow validation endpoint."""

    async def test_validate_empty_dag(self, client: AsyncClient):
        token = await _register_and_get_token(client)

        create_resp = await client.post(
            "/api/v1/workflows",
            json={"workspace_id": "test-ws", "name": "Empty DAG", "dag_json": {}},
            headers=_headers(token),
        )
        wf_id = create_resp.json()["id"]

        response = await client.post(
            f"/api/v1/workflows/{wf_id}/validate",
            headers=_headers(token),
        )
        assert response.status_code == 200
        data = response.json()
        assert not data["valid"]
        assert len(data["errors"]) > 0

    async def test_validate_valid_dag(self, client: AsyncClient):
        token = await _register_and_get_token(client)

        dag = {
            "nodes": [
                {"id": "input_1", "type": "input", "config": {}},
                {"id": "agent_1", "type": "agent", "config": {"system_prompt": "test", "model": {"provider": "openai", "model_id": "gpt-4o-mini"}}},
                {"id": "output_1", "type": "output", "config": {}},
            ],
            "edges": [
                {"source": "input_1", "target": "agent_1"},
                {"source": "agent_1", "target": "output_1"},
            ],
        }

        create_resp = await client.post(
            "/api/v1/workflows",
            json={"workspace_id": "test-ws", "name": "Valid DAG", "dag_json": dag},
            headers=_headers(token),
        )
        wf_id = create_resp.json()["id"]

        response = await client.post(
            f"/api/v1/workflows/{wf_id}/validate",
            headers=_headers(token),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"]
        assert data["node_count"] == 3
        assert data["edge_count"] == 2

    async def test_validate_cyclic_dag(self, client: AsyncClient):
        token = await _register_and_get_token(client)

        dag = {
            "nodes": [
                {"id": "a", "type": "agent", "config": {}},
                {"id": "b", "type": "agent", "config": {}},
            ],
            "edges": [
                {"source": "a", "target": "b"},
                {"source": "b", "target": "a"},
            ],
        }

        create_resp = await client.post(
            "/api/v1/workflows",
            json={"workspace_id": "test-ws", "name": "Cyclic DAG", "dag_json": dag},
            headers=_headers(token),
        )
        wf_id = create_resp.json()["id"]

        response = await client.post(
            f"/api/v1/workflows/{wf_id}/validate",
            headers=_headers(token),
        )
        assert response.status_code == 200
        data = response.json()
        assert not data["valid"]
        assert any("Cycle" in e for e in data["errors"])


@pytest.mark.asyncio
class TestWorkflowExportImport:
    """Test workflow export and import endpoints."""

    async def test_export_json(self, client: AsyncClient):
        token = await _register_and_get_token(client)

        create_resp = await client.post(
            "/api/v1/workflows",
            json={
                "workspace_id": "test-ws",
                "name": "Export Test",
                "dag_json": {"nodes": [{"id": "n1", "type": "agent"}], "edges": []},
            },
            headers=_headers(token),
        )
        wf_id = create_resp.json()["id"]

        response = await client.get(
            f"/api/v1/workflows/{wf_id}/export",
            headers=_headers(token),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Export Test"
        assert "dag" in data
        assert "version" in data

    async def test_import_valid(self, client: AsyncClient):
        token = await _register_and_get_token(client)

        dag = {
            "nodes": [
                {"id": "i", "type": "input", "config": {}},
                {"id": "o", "type": "output", "config": {}},
            ],
            "edges": [{"source": "i", "target": "o"}],
        }

        response = await client.post(
            "/api/v1/workflows/import",
            json={"workspace_id": "test-ws", "name": "Imported", "dag": dag},
            headers=_headers(token),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Imported"

    async def test_import_invalid_dag_rejected(self, client: AsyncClient):
        token = await _register_and_get_token(client)

        dag = {
            "nodes": [
                {"id": "a", "type": "agent"},
                {"id": "b", "type": "agent"},
            ],
            "edges": [
                {"source": "a", "target": "b"},
                {"source": "b", "target": "a"},  # cycle
            ],
        }

        response = await client.post(
            "/api/v1/workflows/import",
            json={"workspace_id": "test-ws", "dag": dag},
            headers=_headers(token),
        )
        assert response.status_code == 400


@pytest.mark.asyncio
class TestWorkflowAuth:
    """Test that workflow endpoints require authentication."""

    async def test_create_without_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/workflows",
            json={"workspace_id": "test", "name": "No Auth"},
        )
        assert response.status_code == 422  # Missing Authorization header

    async def test_list_without_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/workflows")
        assert response.status_code == 422

    async def test_create_with_invalid_token(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/workflows",
            json={"workspace_id": "test", "name": "Bad Token"},
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401
