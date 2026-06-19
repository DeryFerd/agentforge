# AgentForge — Progress Tracker

> **Last Updated:** June 16, 2026 (UI Bug Fix Session — Save/Auth/Dark Mode)

---

## Current Phase: **All Features Implemented — UI Polish + Bug Fixes**

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

## UI Bug Fix Session (June 16)

| Issue | Root Cause | Fix |
|---|---|---|
| Save button stays active after save (v1→v2 without changes) | React Flow fires `onNodesChange` for `select` and `dimensions` events (not just structural edits), which all triggered `setNodes` → `isDirty: true` | Filter non-structural changes in `DAGCanvas.tsx`; use `useWorkflowStore.setState()` directly for select/dimensions without setting isDirty |
| No auth redirect on first load (goes to dashboard instead of login) | Dashboard and editor pages had no auth guard — loaded immediately without checking `access_token` | Added `useEffect` auth guards with `router.replace("/login")`, loading screen prevents flash, also wrapped `useSearchParams` pages in `Suspense` for Next.js build |
| Dashboard flashes briefly before login redirect | `useEffect` runs after first render — server pre-renders full dashboard HTML before JS can redirect | Next.js middleware (`src/middleware.ts`) checks `access_token` cookie server-side before any page renders; login sets cookie alongside localStorage; simplified client-side guards |
| Dark mode not implemented | All 8 pages + 5 DAG components used hardcoded light colors (`bg-white`, `text-gray-900`) with no `dark:` Tailwind variants | Added `dark:` classes to all pages/components; added `@custom-variant dark` to `globals.css` for Tailwind v4 class-based dark mode; DarkModeToggle added to dashboard + editor headers |
| Dark mode toggle stuck on dark (can't switch back to light) | (1) Tailwind v4 defaults to `prefers-color-scheme` media query, ignoring `.dark` class; (2) Next.js React reconciliation resets `<html>` className on re-renders, wiping the `.dark` class | (1) Added `@custom-variant dark (&:where(.dark, .dark *))` to globals.css; (2) Toggle targets `<body>` instead of `<html>` since body isn't reconciled by React |

## UX Polish + Execution Fix (June 18)

| Issue | Root Cause | Fix |
|---|---|---|
| Node numbering is global (Agent 1, Tool 2, Router 3) | Single `nodeCounter` incremented for all node types | Per-type counting: filter existing nodes by type, increment per-type (`Agent 1, Tool 1, Agent 2`) |
| Edge routing looks curved/pulled upward | Handles at Top/Bottom positions with bezier edges | Moved handles to Left/Right + `smoothstep` edge type for clean horizontal flow |
| No warning when clicking Back with unsaved changes | "Back" was a plain `<a>` link with no dirty check | Converted to `<button>` with `window.confirm()` when `isDirty`; added `beforeunload` listener for tab close |
| Workflows stay in "queued" status forever | Execution worker was a separate process that was never started | Embedded worker as asyncio task in FastAPI lifespan with lazy import; worker starts automatically with backend |
| LLM calls fail with "OPENAI_API_KEY not configured" | No LLM provider configured in `.env` | Added `OPENAI_BASE_URL` config for OpenAI-compatible APIs; integrated Ollama Cloud (`https://ollama.com/v1`) |

## Platform Completeness Sprint (June 19)

| Issue | Root Cause | Fix |
|---|---|---|
| Templates page is empty | No seed data in `agent_templates` table | Created `seed_templates.py` with 8 starter templates (Summarizer, Code Reviewer, Data Extractor, Sentiment Analyzer, Q&A Agent, Content Writer, Translation Agent, Research Assistant); seeded on startup via lifespan |
| MCP Servers page is empty | No servers registered in `mcp_servers` table | Created `seed_mcp_servers.py` with 3 built-in servers (filesystem, web-search, postgres); seeded on startup |
| Cost dashboard shows $0.00 | Ollama Cloud models had $0 pricing | Updated MODEL_PRICING with realistic Ollama Cloud rates ($0.50–$4.50/1M tokens); costs now flow through execution → CostRecord → dashboard |
| Dashboard workflow cards lack execution data | List endpoint only returns workflow metadata | Added `/workflows/dashboard/summary` endpoint with execution count, last run status, total cost per workflow; enhanced frontend cards with stats display |
| Dashboard stats cards show static data | No aggregation queries | Computed totalExecutions and totalCost from summary endpoint; wired to stats cards |

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
| June 15 2026 | E2E Bug Fixes | 4 critical E2E bugs fixed: React Flow state sync, auto-create workspace, URL sync after save, dag_json in API response |
| June 16 2026 | UI Bug Fixes | Save isDirty fix, auth redirect guard, full dark mode across all pages/components, dark mode toggle fix |
| June 18 2026 | UX Polish + Execution | Per-type node numbering, left/right handles, unsaved warning, execution worker embedded in lifespan, Ollama Cloud LLM integration |
| June 19 2026 | **Platform Completeness** | **8 seed templates, 3 seed MCP servers, cost tracking wired end-to-end, dashboard summary endpoint with execution stats** |
