"""AgentForge FastAPI application entry point."""

import json
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.rate_limit import RateLimitMiddleware
from app.core.security_middleware import SecurityHeadersMiddleware

logger = structlog.get_logger()
settings = get_settings()


# ─── WebSocket Connection Manager ─────────────────────────────────


class ConnectionManager:
    """Simple in-memory WebSocket connection manager for execution events."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, run_id: str):
        await websocket.accept()
        if run_id not in self.active_connections:
            self.active_connections[run_id] = []
        self.active_connections[run_id].append(websocket)

    def disconnect(self, websocket: WebSocket, run_id: str):
        if run_id in self.active_connections:
            self.active_connections[run_id] = [
                c for c in self.active_connections[run_id] if c != websocket
            ]
            if not self.active_connections[run_id]:
                del self.active_connections[run_id]

    async def send_event(self, run_id: str, event: dict[str, Any]):
        if run_id in self.active_connections:
            dead = []
            for conn in self.active_connections[run_id]:
                try:
                    await conn.send_text(json.dumps(event, default=str))
                except Exception:
                    dead.append(conn)
            for conn in dead:
                self.active_connections[run_id].remove(conn)


ws_manager = ConnectionManager()


# ─── Lifespan ─────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown hooks."""
    # Setup tracing
    from app.services.tracing import setup_tracing
    setup_tracing()

    # Setup Langfuse
    from app.services.langfuse_integration import get_langfuse
    get_langfuse()

    logger.info("AgentForge starting up", version=settings.app_version)
    yield

    # Flush Langfuse
    from app.services.langfuse_integration import flush as langfuse_flush
    langfuse_flush()

    logger.info("AgentForge shutting down")


# ─── App ──────────────────────────────────────────────────────────


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Open-Source Multi-Agent Workflow Orchestrator",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Security headers (OWASP)
app.add_middleware(SecurityHeadersMiddleware)

# Rate limiting
app.add_middleware(RateLimitMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 routes
app.include_router(api_v1_router, prefix=settings.api_prefix)


# ─── Health ────────────────────────────────────────────────────────


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.app_version}


# ─── WebSocket ─────────────────────────────────────────────────────


@app.websocket("/ws/executions/{run_id}")
async def websocket_execution(websocket: WebSocket, run_id: str):
    """WebSocket endpoint for real-time execution event streaming.

    Clients connect here to receive live updates as a workflow executes.
    Also handles HITL (Human-in-the-Loop) approval responses.
    """
    await ws_manager.connect(websocket, run_id)
    logger.info("WebSocket connected", run_id=run_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            else:
                # Handle HITL responses and other commands
                try:
                    message = json.loads(data)
                    msg_type = message.get("type")
                    if msg_type == "hitl_response":
                        # Forward HITL response to the execution worker
                        logger.info(
                            "HITL response received",
                            run_id=run_id,
                            node_id=message.get("node_id"),
                            decision=message.get("decision"),
                        )
                        # The execution worker polls for HITL responses
                        # Store in Redis for the worker to pick up
                        import redis.asyncio as aioredis
                        redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
                        await redis_client.set(
                            f"hitl:{run_id}:{message.get('node_id')}",
                            json.dumps(message),
                            ex=86400,  # 24h TTL
                        )
                        await redis_client.aclose()
                        # Notify all connected clients
                        await ws_manager.send_event(run_id, {
                            "type": "execution_resumed",
                            "node_id": message.get("node_id"),
                            "decision": message.get("decision"),
                        })
                except json.JSONDecodeError:
                    pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, run_id)
        logger.info("WebSocket disconnected", run_id=run_id)


async def publish_execution_event(run_id: str, event: dict[str, Any]):
    """Publish an execution event to all connected WebSocket clients."""
    await ws_manager.send_event(run_id, event)
