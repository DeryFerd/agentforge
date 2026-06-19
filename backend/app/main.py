"""AgentForge FastAPI application entry point."""

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any

import redis.asyncio as aioredis
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
    """In-memory WebSocket connection manager with Redis pub/sub relay.

    Architecture:
    - Each execution run_id has a list of connected WebSocket clients
    - Worker publishes events to Redis channel `agentforge:ws:{run_id}`
    - This manager subscribes to Redis channels and relays to WebSocket clients
    - Single shared Redis connection for subscriptions (no per-message leaks)
    """

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
        self._redis: aioredis.Redis | None = None
        self._pubsub: aioredis.client.PubSub | None = None
        self._relay_task: asyncio.Task | None = None

    async def start_relay(self):
        """Start the Redis pub/sub relay. Call during app lifespan startup."""
        self._redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        self._pubsub = self._redis.pubsub()
        self._relay_task = asyncio.create_task(self._relay_loop())
        logger.info("WebSocket relay started")

    async def stop_relay(self):
        """Stop the Redis pub/sub relay. Call during app lifespan shutdown."""
        if self._relay_task:
            self._relay_task.cancel()
            try:
                await self._relay_task
            except asyncio.CancelledError:
                pass
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.aclose()
        if self._redis:
            await self._redis.aclose()
        logger.info("WebSocket relay stopped")

    async def _relay_loop(self):
        """Listen to Redis pub/sub and relay messages to WebSocket clients."""
        try:
            async for message in self._pubsub.listen():
                if message["type"] == "message":
                    channel = message["channel"]
                    # Channel format: agentforge:ws:{run_id}
                    if isinstance(channel, str) and channel.startswith("agentforge:ws:"):
                        run_id = channel.replace("agentforge:ws:", "")
                        await self._broadcast(run_id, message["data"])
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Relay loop error", error=str(e))

    async def _broadcast(self, run_id: str, data: str):
        """Send a message to all WebSocket clients for a given run_id."""
        if run_id not in self.active_connections:
            return
        dead = []
        for conn in self.active_connections[run_id]:
            try:
                await conn.send_text(data)
            except Exception:
                dead.append(conn)
        for conn in dead:
            self.active_connections[run_id].remove(conn)

    async def connect(self, websocket: WebSocket, run_id: str):
        await websocket.accept()
        if run_id not in self.active_connections:
            self.active_connections[run_id] = []
            # Subscribe to Redis channel for this run
            if self._pubsub:
                await self._pubsub.subscribe(f"agentforge:ws:{run_id}")
        self.active_connections[run_id].append(websocket)

    def disconnect(self, websocket: WebSocket, run_id: str):
        if run_id in self.active_connections:
            self.active_connections[run_id] = [
                c for c in self.active_connections[run_id] if c != websocket
            ]
            if not self.active_connections[run_id]:
                del self.active_connections[run_id]
                # Unsubscribe from Redis channel
                if self._pubsub:
                    asyncio.create_task(
                        self._pubsub.unsubscribe(f"agentforge:ws:{run_id}")
                    )


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

    # Start WebSocket relay (Redis pub/sub)
    await ws_manager.start_relay()

    # Seed built-in templates and MCP servers (idempotent — runs once)
    from app.core.database import async_session_factory
    from app.core.seed_templates import seed_templates
    from app.core.seed_mcp_servers import seed_mcp_servers
    try:
        async with async_session_factory() as seed_db:
            await seed_templates(seed_db)
            await seed_mcp_servers(seed_db)
            await seed_db.commit()
    except Exception as e:
        logger.warning("Seed data initialization failed (non-fatal)", error=str(e))

    # Start execution worker (picks up jobs from Redis queue)
    # Lazy import to avoid blocking app startup with heavy engine deps
    async def _start_worker():
        from app.workers.execution_worker import worker_loop
        await worker_loop()

    worker_task = asyncio.create_task(_start_worker())

    logger.info("AgentForge starting up", version=settings.app_version)
    yield

    # Stop execution worker
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass

    # Flush Langfuse
    from app.services.langfuse_integration import flush as langfuse_flush
    langfuse_flush()

    # Stop WebSocket relay
    await ws_manager.stop_relay()

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
    Events are relayed from the execution worker via Redis pub/sub.
    Also handles HITL (Human-in-the-Loop) approval responses.
    """
    await ws_manager.connect(websocket, run_id)
    logger.info("WebSocket connected", run_id=run_id)

    # Shared Redis client for HITL responses (created once per connection)
    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            else:
                try:
                    message = json.loads(data)
                    msg_type = message.get("type")
                    if msg_type == "hitl_response":
                        logger.info(
                            "HITL response received",
                            run_id=run_id,
                            node_id=message.get("node_id"),
                            decision=message.get("decision"),
                        )
                        # Store in Redis for the worker to pick up
                        await redis_client.set(
                            f"hitl:{run_id}:{message.get('node_id')}",
                            json.dumps(message),
                            ex=86400,
                        )
                        # Publish event via Redis pub/sub (relayed to all clients)
                        await redis_client.publish(
                            f"agentforge:ws:{run_id}",
                            json.dumps({
                                "type": "execution_resumed",
                                "node_id": message.get("node_id"),
                                "decision": message.get("decision"),
                            }),
                        )
                except json.JSONDecodeError:
                    pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, run_id)
        logger.info("WebSocket disconnected", run_id=run_id)
    finally:
        await redis_client.aclose()
