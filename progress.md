# AgentForge — Progress Tracker

> **Last Updated:** June 15, 2026 (Live Debug Session — E2E Bug Fixes)

---

## Current Phase: **All Features Implemented — Live Verified + E2E Bug Fixes**

---

## Phase 0–3: All Done (see STRUCTURE.md for details)

## Phase 4–8: All Done (see STRUCTURE.md for details)

---

## Roast Review Fixes (from ROAST_REVIEW.md)

### Critical (Kill List)
| Issue | Status | Fix |
|---|---|---|
| `eval()` in RouterNodeExecutor | **Fixed** | Replaced with `simpleeval` library |
| HITL auto-approves everything | **Fixed** | Real Redis polling, timeout rejects |
| Git history reveals 2-evening build | Deferred | Requires interactive rebase |

### Major — All Fixed
- OTel spans wired into executors + worker
- Engine tests: 25+ tests (compiler, all executors, safeeval security)
- SQLite → testcontainers-postgres with fallback
- No live demo URL — deferred

### Minor — All Fixed
- WebSocket Redis leak → pub/sub relay
- Docker Compose `version` removed, `stop_signal` added
- `.dockerignore` added, README URL fixed
- Evaluator cost tracking, 5 ADRs created

---

## Runtime Fixes (Live Debug — June 15)

### Infrastructure
| Issue | Root Cause | Fix |
|---|---|---|
| Backend fails to start | `langfuse.callback` removed in v4.x | Use `Langfuse` client directly |
| `pip install -e .` fails | setuptools multi-package detection | `[tool.setuptools.packages.find] include = ["app*"]` |
| Register returns 500 | `passlib` incompatible with `bcrypt >= 4.1` | Direct `bcrypt.hashpw()`/`checkpw()` |
| `GET /workflows` returns 422 | `Header(...)` required → 422 | `Header(None)` + explicit 401 |

### E2E Workflow Bugs (found during live testing)
| Issue | Root Cause | Fix | Commit |
|---|---|---|---|
| Nodes don't appear on canvas | React Flow `useNodesState` creates local state that doesn't sync with Zustand store | Removed `useNodesState`/`useEdgesState`, use Zustand store directly with `applyNodeChanges`/`applyEdgeChanges` | `dag_canvas_fix` |
| Save returns "Network Error" | `workspace_id: "default"` not a valid UUID → FK violation → 500 → axios shows as network error | Auto-create workspace via API if none exists; extract `error.response.data.detail` for meaningful messages | `e856afe` |
| Save creates new workflow instead of updating | After first save, URL stays at `/editor` (no `?id=xxx`) → store `workflowId` lost on navigation | `useEffect` watches `storeWorkflowId` → `router.replace(/editor?id=xxx)` | `a962df1` |
| Saved workflow nodes disappear on reload | `WorkflowResponse` model didn't include `dag_json` field → `loadWorkflow()` gets undefined | Added `dag_json: dict | None` to `WorkflowResponse` + `_to_response()` | `1399b76` |

---

## Changelog

| Date | Session | Change |
|---|---|---|
| June 11 2026 | Phase 0–3 | Full build: monorepo, backend, frontend, engine, tests |
| June 11 2026 | Session 2 | Frontend polish: save wiring, login, workspaces, node config, execution history |
| June 11 2026 | Session 3 | LLM client, MCP client, checkpointer, rate limiting, API keys, webhooks, OAuth, WebSocket, templates, MCP/template/cost UI, E2E tests |
| June 11 2026 | Session 4 | Budget enforcement, OTel tracing, Langfuse integration, HITL WebSocket, error boundaries, versioning UI, dark mode, agent memory, security hardening |
| June 13 2026 | Roast Fixes | Kill eval(), real HITL, OTel spans wired, engine tests, testcontainers, WebSocket leak, Docker fix, ADRs |
| June 15 2026 | Live Debug | langfuse v4, setuptools, bcrypt, auth 401, Docker + migrations + full stack verified |
| June 15 2026 | **E2E Bug Fixes** | **4 critical E2E bugs fixed: React Flow state sync, auto-create workspace, URL sync after save, dag_json in API response** |
