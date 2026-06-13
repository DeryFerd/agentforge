# ADR-005: FastAPI + Async Python over Django/Sync for API Layer

**Status:** Accepted
**Date:** 2026-06-11

## Context

The API layer must handle: concurrent workflow executions, WebSocket connections, LLM API calls (which are I/O-bound), Redis queue operations, and real-time event streaming. The framework choice affects throughput, developer experience, and ecosystem compatibility.

## Options Considered

### 1. FastAPI + async (Selected)
- **Pros:** Native async/await — critical for concurrent LLM calls and WebSocket handling. Auto-generated OpenAPI spec (`/docs`). Pydantic v2 integration for request/response validation. SQLAlchemy 2.0 async support. Highest throughput among Python web frameworks for I/O-bound workloads. Structured logging via structlog.
- **Cons:** Smaller ecosystem than Django. No built-in admin panel. No ORM included.

### 2. Django + DRF
- **Pros:** Massive ecosystem. Built-in admin panel. ORM included. Battle-tested at scale.
- **Cons:** Sync-first architecture — async views are second-class. DRF serializer overhead. Heavier footprint. WebSocket support via Channels adds complexity.

### 3. Starlette (raw)
- **Pros:** Minimal. Fast. Full async.
- **Cons:** Too minimal — no auto docs, no dependency injection, no Pydantic integration.

## Decision

**FastAPI** — the async-native architecture is essential for an orchestration platform that makes concurrent LLM API calls, handles WebSocket connections, and processes Redis queues simultaneously. The auto-generated OpenAPI spec doubles as documentation. Pydantic v2 settings provide type-safe configuration.

## Consequences

- All API routers use `async def` — no blocking calls in the event loop
- WebSocket endpoint (`/ws/executions/{run_id}`) works natively without Channels
- SQLAlchemy 2.0 async sessions (`AsyncSession`) for all database operations
- OpenAPI spec auto-generated at `/docs` — no manual API documentation needed
- Dependency injection via `Depends()` for auth, DB sessions, RBAC
- Trade-off: no built-in admin panel (acceptable — our dashboard serves this purpose)
