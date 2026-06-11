"""API v1 router aggregation — mounts all sub-routers."""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.costs import router as costs_router
from app.api.v1.executions import router as executions_router
from app.api.v1.mcp_servers import router as mcp_router
from app.api.v1.templates import router as templates_router
from app.api.v1.webhooks import router as webhooks_router
from app.api.v1.workflows import router as workflows_router
from app.api.v1.workspaces import router as workspaces_router

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(workspaces_router, prefix="/workspaces", tags=["workspaces"])
api_v1_router.include_router(workflows_router, prefix="/workflows", tags=["workflows"])
api_v1_router.include_router(executions_router, prefix="/executions", tags=["executions"])
api_v1_router.include_router(templates_router, prefix="/templates", tags=["templates"])
api_v1_router.include_router(mcp_router, prefix="/mcp-servers", tags=["mcp-servers"])
api_v1_router.include_router(costs_router, prefix="/costs", tags=["costs"])
api_v1_router.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])
