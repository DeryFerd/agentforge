# AgentForge — Progress Tracker

> **Last Updated:** June 15, 2026 (Live Debug Session)

---

## Current Phase: **All Features Implemented — Live Verified**

---

## Phase 0–3: All Done (see STRUCTURE.md for details)

## Phase 4–8: All Done (see STRUCTURE.md for details)

---

## Roast Review Fixes (from ROAST_REVIEW.md)

### Critical (Kill List)
| Issue | Status | Fix |
|---|---|---|
| `eval()` in RouterNodeExecutor | **Fixed** | Replaced with `simpleeval` library — safe expression evaluator that blocks code execution |
| HITL auto-approves everything | **Fixed** | Real implementation: polls Redis for human response, timeout rejects, error on rejection |
| Git history reveals 2-evening build | Deferred | Requires interactive rebase — not done in code |

### Major
| Issue | Status | Fix |
|---|---|---|
| OTel spans defined but never called | **Fixed** | All executors wrap with `_wrap_with_span()`, worker uses `span_workflow_execution()`, LLM calls use `span_llm_call()` |
| No engine tests | **Fixed** | `test_engine.py`: 25+ tests covering compiler, all 7 executors, full pipeline, safeeval security |
| SQLite tests vs PostgreSQL | **Fixed** | `conftest.py` now uses `testcontainers-python` with real PostgreSQL, SQLite fallback |
| No live demo URL | Deferred | Requires cloud deployment |

### Minor — All Fixed
- WebSocket Redis connection leak → pub/sub relay
- Docker Compose `version: "3.9"` → removed, added `stop_signal: SIGTERM`
- No `.dockerignore` → added for both backend and frontend
- `yourusername` in README → `DeryFerd`
- Evaluator cost tracking → now returns actual tokens/cost from LLM judge
- No ADRs → 5 ADRs created

---

## Runtime Fixes (Live Debug Session — June 15)

| Issue | Root Cause | Fix |
|---|---|---|
| Backend fails to start | `langfuse.callback` module removed in v4.x | Removed deprecated import, use `Langfuse` client directly |
| `pip install -e .` fails | setuptools finds `app` + `alembic` as multiple packages | Added `[tool.setuptools.packages.find] include = ["app*"]` |
| Register returns 500 | `passlib` incompatible with `bcrypt >= 4.1` | Replaced with direct `bcrypt.hashpw()` / `bcrypt.checkpw()` |
| `GET /workflows` returns 422 | `Header(...)` makes auth header required → FastAPI 422 | Changed to `Header(None)` + explicit 401 when missing |
| Docker Compose needs `.env` | Compose references `.env` file | Copy `.env.example` → `.env` |

---

## Changelog

| Date | Session | Change |
|---|---|---|
| June 11 2026 | Phase 0–3 | Full build: monorepo, backend, frontend, engine, tests |
| June 11 2026 | Session 2 | Frontend polish: save wiring, login, workspaces, node config, execution history |
| June 11 2026 | Session 3 | LLM client, MCP client, checkpointer, rate limiting, API keys, webhooks, OAuth, WebSocket, templates, MCP/template/cost UI, E2E tests |
| June 11 2026 | Session 4 | Budget enforcement, OTel tracing, Langfuse integration, HITL WebSocket, error boundaries, versioning UI, dark mode, agent memory, security hardening |
| June 13 2026 | Roast Fixes | Kill eval(), real HITL, OTel spans wired, engine tests, testcontainers, WebSocket leak, Docker fix, ADRs |
| June 15 2026 | **Live Debug** | **langfuse v4 fix, setuptools fix, bcrypt direct, auth 401 fix, Docker + migrations + full stack verified working** |
