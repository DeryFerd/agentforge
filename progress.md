# AgentForge — Progress Tracker

> **Last Updated:** June 13, 2026 (Roast Fix Session)

---

## Current Phase: **Roast Review Fixes Applied**

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

### Minor
| Issue | Status | Fix |
|---|---|---|
| WebSocket Redis connection leak | **Fixed** | Redis pub/sub relay with single shared connection, per-connection client for HITL |
| Docker Compose `version: "3.9"` | **Fixed** | Removed deprecated `version` field, added `stop_signal: SIGTERM` for worker |
| No `.dockerignore` | **Fixed** | Added for both backend and frontend |
| `yourusername` in README | **Fixed** | Changed to `DeryFerd` |
| Evaluator doesn't track LLM costs | **Fixed** | EvaluatorNodeExecutor now tracks `tokens_in`, `tokens_out`, `cost_usd` from judge LLM |
| No ADRs | **Fixed** | 5 ADRs: LangGraph, PostgreSQL checkpointing, React Flow, simpleeval, FastAPI |

### Dependencies Added
- `simpleeval>=1.0.0` — safe expression evaluation
- `testcontainers[postgres]>=4.0.0` — PostgreSQL test containers

---

## Changelog

| Date | Session | Change |
|---|---|---|
| June 11 2026 | Phase 0–3 | Full build: monorepo, backend, frontend, engine, tests |
| June 11 2026 | Session 2 | Frontend polish: save wiring, login, workspaces, node config, execution history |
| June 11 2026 | Session 3 | LLM client, MCP client, checkpointer, rate limiting, API keys, webhooks, OAuth, WebSocket, templates, MCP/template/cost UI, E2E tests |
| June 11 2026 | Session 4 | Budget enforcement, OTel tracing, Langfuse integration, HITL WebSocket, error boundaries, versioning UI, dark mode, agent memory, security hardening |
| June 13 2026 | Roast Fixes | **Kill eval() (simpleeval), real HITL (Redis polling), wire OTel spans into executors+worker, engine tests (25+), testcontainers PostgreSQL, fix WebSocket Redis leak, Docker Compose fix, .dockerignore, README fix, evaluator cost tracking, 5 ADRs** |
