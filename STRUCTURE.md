# AgentForge — Final Architecture & File Structure

> Complete map of the codebase: every file, its purpose, and how it connects to others.

---

## High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BROWSER (User)                                  │
│                                                                              │
│   localhost:3000                                                             │
│   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────────┐  │
│   │  Dashboard │  │   Editor   │  │ Executions │  │ Templates/MCP/Cost │  │
│   │  page.tsx  │  │  page.tsx  │  │  page.tsx  │  │     page.tsx       │  │
│   └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────────┬──────────┘  │
│         │               │               │                    │              │
│         └───────────────┴───────────────┴────────────────────┘              │
│                                  │                                           │
│                    ┌─────────────┴─────────────┐                            │
│                    │    api.ts (axios client)    │                           │
│                    │  + workflow-store (Zustand) │                           │
│                    │  + useExecutionWebSocket    │                           │
│                    └─────────────┬──────────────┘                           │
└──────────────────────────────────┼──────────────────────────────────────────┘
                                   │
                    HTTP REST (/api/v1/*)  +  WebSocket (/ws/executions/{id})
                                   │
┌──────────────────────────────────┼──────────────────────────────────────────┐
│                          BACKEND (FastAPI)                                   │
│                          localhost:8000                                      │
│                                                                              │
│   ┌─────────────────────────────┐                                           │
│   │         main.py             │  ← SecurityHeaders + RateLimit + CORS    │
│   │  lifespan: OTel + Langfuse  │  ← WebSocket: ConnectionManager          │
│   └──────────────┬──────────────┘                                           │
│                  │                                                           │
│   ┌──────────────┴──────────────┐                                           │
│   │      api/v1/router.py       │  ← 10 sub-routers mounted               │
│   └──┬───┬───┬───┬───┬───┬──┬──┘                                          │
│      │   │   │   │   │   │  │                                               │
│   auth oauth work- flows exec- templates mcp costs webhooks api-keys       │
│              spaces         utions                                           │
│      │   │   │   │   │   │  │                                               │
│      └───┴───┴───┴───┴───┴──┘                                              │
│                  │                                                           │
│   ┌──────────────┴──────────────┐                                           │
│   │    core/ (shared modules)    │                                           │
│   │  config.py   → settings      │                                           │
│   │  database.py → DB session    │                                           │
│   │  deps.py     → auth/RBAC     │                                           │
│   │  security.py → JWT/bcrypt    │                                           │
│   │  rate_limit  → middleware    │                                           │
│   │  security_mw → OWASP headers │                                           │
│   └──────────────┬──────────────┘                                           │
│                  │                                                           │
│   ┌──────────────┴──────────────┐                                           │
│   │   engine/ (execution core)   │                                           │
│   │  compiler.py    → DAG→Graph  │                                           │
│   │  executors.py   → 7 node types│                                          │
│   │  llm_client.py  → LLM calls  │                                           │
│   │  validator.py   → DAG checks │                                           │
│   │  checkpointer   → crash rec. │                                           │
│   └──────────────┬──────────────┘                                           │
│                  │                                                           │
│   ┌──────────────┴──────────────┐                                           │
│   │    models/ (SQLAlchemy)      │                                           │
│   │  user, workspace, workflow,  │                                           │
│   │  execution, misc, api_key,   │                                           │
│   │  agent_memory                │                                           │
│   └──────────────┬──────────────┘                                           │
│                  │                                                           │
│   ┌──────────────┴──────────────┐     ┌─────────────────────────┐          │
│   │    services/                 │     │    workers/              │          │
│   │  budget.py → cost limits    │     │  execution_worker.py    │          │
│   │  tracing.py → OTel spans    │     │  Redis BLPOP → compile  │          │
│   │  langfuse  → LLM traces     │     │  → execute → persist    │          │
│   │  webhook_d → HMAC delivery  │     └─────────────────────────┘          │
│   └─────────────────────────────┘                                           │
│                                                                              │
│   ┌─────────────────────────────┐                                           │
│   │    mcp/client.py            │  ← MCP stdio + SSE tool calls            │
│   └─────────────────────────────┘                                           │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
┌─────────────┴─────┐ ┌───────────┴──────┐ ┌──────────┴──────────┐
│   PostgreSQL       │ │     Redis        │ │     MinIO (S3)      │
│   :5432            │ │     :6379        │ │     :9000           │
│   13 tables        │ │   task queue     │ │   file storage      │
│   (via Alembic)    │ │   HITL store     │ │                     │
└────────────────────┘ └──────────────────┘ └─────────────────────┘
                                                        │
                                              ┌─────────┴──────────┐
                                              │  Langfuse           │
                                              │  :3001              │
                                              │  LLM observability  │
                                              └────────────────────┘
```

---

## File-by-File Map

### Root Level

| File | Purpose | Connects To |
|---|---|---|
| `docker-compose.yml` | Orchestrates 7 Docker services | All backend/frontend/infra services |
| `.env.example` | Environment variable template | `config.py`, `docker-compose.yml` |
| `.gitignore` | Git ignore rules | — |
| `README.md` | Project overview + quickstart | All docs |
| `LICENSE` | Apache 2.0 | — |
| `CONTRIBUTING.md` | Contributor guide | — |
| `PRD.md` | Product requirements | `system-design.md`, `plan.md` |
| `system-design.md` | Technical architecture | `STRUCTURE.md` (this file) |
| `agents.md` | Agent behavior spec | `executors.py`, `templates/*.yaml` |
| `plan.md` | Implementation plan (8 phases) | `progress.md` |
| `progress.md` | Task tracker (live) | `plan.md` |
| `memory.md` | Session journal (local-only) | — |
| `handoff.md` | Handoff notes (local-only) | — |
| `RESEARCH-*.md` | Market research + job analysis | `PRD.md` |

### Backend — `backend/`

#### Entry Point & App Setup

| File | Purpose | Imports / Uses | Used By |
|---|---|---|---|
| `app/main.py` | FastAPI app, middleware, WebSocket, lifespan | `config.py`, `rate_limit.py`, `security_middleware.py`, `router.py`, `tracing.py`, `langfuse_integration.py` | Uvicorn, Docker |
| `Dockerfile` | Python 3.12 image for API + Worker | `pyproject.toml` | `docker-compose.yml` |
| `pyproject.toml` | Dependencies + tool config | — | `pip install` |

#### Core — `backend/app/core/`

| File | Purpose | Imports / Uses | Used By |
|---|---|---|---|
| `config.py` | `Settings` class (pydantic-settings), `get_settings()` | `.env` file | Every module that needs config |
| `database.py` | Async SQLAlchemy engine, `Base`, `get_db()` dependency | `config.py` (DATABASE_URL) | All API routers, models, Alembic |
| `deps.py` | `get_current_user`, `RequireRole`, `log_audit()` | `security.py`, `database.py`, `user.py`, `workspace.py` | All auth-protected endpoints |
| `security.py` | `hash_password()`, `verify_password()`, `create_access_token()`, `create_refresh_token()`, `decode_token()` | `config.py` (JWT settings) | `auth.py`, `deps.py`, `oauth.py` |
| `rate_limit.py` | `RateLimitMiddleware` — per-IP, API key bypass | `config.py` | `main.py` (added as middleware) |
| `security_middleware.py` | `SecurityHeadersMiddleware` (OWASP), `InputSanitizer`, `validate_dag_structure()` | — | `main.py`, `workflows.py` |

#### API Routers — `backend/app/api/v1/`

| File | Prefix | Endpoints | Uses Models | Uses Core |
|---|---|---|---|---|
| `router.py` | — | Aggregates all 10 routers below | — | — |
| `auth.py` | `/auth` | POST register, login, refresh; GET /me | `user.User` | `deps.py`, `security.py`, `database.py` |
| `oauth.py` | `/auth/oauth` | GET/POST github/*, google/* | `user.User`, `workspace.*` | `security.py`, `database.py`, `config.py` |
| `workspaces.py` | `/workspaces` | CRUD + member invite/list | `workspace.*` | `deps.py`, `database.py` |
| `workflows.py` | `/workflows` | CRUD + validate + export + import | `workflow.*` | `deps.py`, `database.py`, `validator.py` |
| `executions.py` | `/executions` | trigger, list, get, trace, cancel | `execution.*`, `workflow.*` | `deps.py`, `database.py`, Redis |
| `templates.py` | `/templates` | CRUD + search | `misc.AgentTemplate` | `deps.py`, `database.py` |
| `mcp_servers.py` | `/mcp-servers` | register, list, delete, health | `misc.MCPServer` | `deps.py`, `database.py` |
| `costs.py` | `/costs` | dashboard, per-workflow, per-execution | `misc.CostRecord` | `deps.py`, `database.py` |
| `webhooks.py` | `/webhooks` | CRUD + trigger | `misc.WebhookTrigger` | `deps.py`, `database.py` |
| `api_keys.py` | `/api-keys` | create, list, revoke, rotate | `api_key.ApiKey` | `deps.py`, `database.py` |

#### Engine — `backend/app/engine/`

| File | Purpose | Imports / Uses | Used By |
|---|---|---|---|
| `compiler.py` | `WorkflowCompiler` — transforms DAG JSON → LangGraph `StateGraph` | `langgraph` | `execution_worker.py` |
| `executors.py` | 7 node executors: Input, Output, Agent, Tool, Router, Evaluator, HITL | `llm_client.py`, `mcp/client.py` | `compiler.py` (via `get_default_executors()`) |
| `llm_client.py` | `call_llm()` — unified OpenAI/Anthropic/Google client with cost calc | `langchain_openai`, `langchain_anthropic`, `langchain_google_genai`, `config.py` | `executors.py` (AgentNodeExecutor) |
| `validator.py` | `DAGValidator` — cycle detection (Kahn's), orphan nodes, type/config checks | — | `workflows.py` (validate endpoint) |
| `checkpointer.py` | `get_checkpointer()` — PostgreSQL checkpointer for LangGraph | `langgraph.checkpoint.postgres`, `config.py` | `execution_worker.py` |

#### Models — `backend/app/models/`

| File | Tables | Relations |
|---|---|---|
| `user.py` | `users` | → workspace.owner_id, workflow.created_by, execution.triggered_by |
| `workspace.py` | `workspaces`, `workspace_members` | ← users (owner, members), → workflows, mcp_servers, api_keys, agent_memories |
| `workflow.py` | `workflows`, `workflow_versions` | ← workspaces, → executions, agent_memories |
| `execution.py` | `executions`, `execution_nodes` | ← workflows, users → cost_records |
| `misc.py` | `agent_templates`, `mcp_servers`, `cost_records`, `audit_logs`, `webhook_triggers` | ← users, workspaces, executions |
| `api_key.py` | `api_keys` | ← workspaces, users |
| `agent_memory.py` | `agent_memories` | ← workspaces, workflows |

#### Services — `backend/app/services/`

| File | Purpose | Used By |
|---|---|---|
| `budget.py` | `check_budget()`, `check_node_budget()`, `BudgetExceededError` | `execution_worker.py`, `executions.py` |
| `tracing.py` | `setup_tracing()`, span helpers (workflow, node, LLM, MCP) | `main.py` (lifespan), `execution_worker.py` |
| `langfuse_integration.py` | `get_langfuse()`, `trace_workflow()`, `trace_node()`, `get_langfuse_handler()`, `flush()` | `main.py` (lifespan), `execution_worker.py` |
| `webhook_delivery.py` | `deliver_webhook()` (HMAC-SHA256 + 3x retry), `verify_webhook_signature()` | `execution_worker.py`, `webhooks.py` |

#### Workers — `backend/app/workers/`

| File | Purpose | Uses |
|---|---|---|
| `execution_worker.py` | Redis BLPOP loop → load workflow → compile (LangGraph) → execute nodes → persist results + cost records + Langfuse traces | `compiler.py`, `executors.py`, `checkpointer.py`, `database.py`, `tracing.py`, `langfuse_integration.py`, `budget.py`, `webhook_delivery.py` |

#### MCP — `backend/app/mcp/`

| File | Purpose | Used By |
|---|---|---|
| `client.py` | `call_mcp_tool()` (stdio + SSE), `list_mcp_tools()` | `executors.py` (ToolNodeExecutor) |

#### Alembic Migrations — `backend/alembic/`

| File | What it creates |
|---|---|
| `env.py` | Async migration config, imports all models |
| `0001_initial_schema.py` | 12 tables: users, workspaces, workspace_members, workflows, workflow_versions, executions, execution_nodes, agent_templates, mcp_servers, cost_records, audit_logs, webhook_triggers |
| `0002_api_keys.py` | `api_keys` table |
| `0003_agent_memories.py` | `agent_memories` table |

#### Tests — `backend/tests/`

| File | Tests | Covers |
|---|---|---|
| `conftest.py` | Fixtures: async SQLite DB, test client | All tests |
| `test_auth.py` | 14 tests | Register, login, /me, refresh, health |
| `test_validator.py` | 25+ tests | Cycle detection, orphan nodes, types, edges, config warnings |
| `test_workflows.py` | Integration tests | CRUD, validation, export/import, auth required |

---

### Frontend — `frontend/`

#### App Pages — `frontend/src/app/`

| File | Route | Purpose | Uses |
|---|---|---|---|
| `layout.tsx` | (all) | Root layout, metadata, dark mode script, ErrorBoundary wrapper | `ErrorBoundaryWrapper.tsx` |
| `page.tsx` | `/` | Dashboard — workflow list, stats, nav links to all pages | `api.ts`, `workflow-store.ts`, `types.ts` |
| `editor/page.tsx` | `/editor[?id=]` | DAG editor — canvas, toolbar, config panel, save/run/validate | `DAGCanvas`, `NodeToolbar`, `NodeConfigPanel`, `workflow-store.ts`, `executionApi` |
| `login/page.tsx` | `/login` | Login/register form, JWT stored in localStorage | `authApi` |
| `workspaces/page.tsx` | `/workspaces` | Create/select workspace, stored in localStorage | `workspaceApi` |
| `executions/page.tsx` | `/executions[?workflow_id=]` | Execution history with expandable per-node trace | `executionApi` |
| `templates/page.tsx` | `/templates` | Template marketplace — search, category filter, install | `api.ts` |
| `mcp-servers/page.tsx` | `/mcp-servers` | MCP server management — register, health check, delete | `api.ts` |
| `cost/page.tsx` | `/cost` | Cost dashboard — model breakdown, pricing reference | `api.ts` |
| `globals.css` | (all) | Tailwind CSS imports + custom styles | `layout.tsx` |

#### Components — `frontend/src/components/`

| File | Purpose | Used By |
|---|---|---|
| `ErrorBoundary.tsx` | React class component — catches render errors, retry/home buttons | `ErrorBoundaryWrapper.tsx` |
| `ErrorBoundaryWrapper.tsx` | Server-component wrapper for ErrorBoundary | `layout.tsx` |
| `DarkModeToggle.tsx` | Sun/Moon toggle with localStorage persistence | Header (any page) |

#### DAG Components — `frontend/src/components/dag/`

| File | Purpose | Used By |
|---|---|---|
| `DAGCanvas.tsx` | React Flow canvas with custom nodes, minimap, controls, snap-to-grid | `editor/page.tsx` |
| `AgentForgeNode.tsx` | Custom React Flow node — 7 types with color + icon | `DAGCanvas.tsx` |
| `NodeToolbar.tsx` | Sidebar to add nodes (Agent, Tool, Router, Evaluator, HITL, Input, Output) | `DAGCanvas.tsx` |
| `NodeConfigPanel.tsx` | Right sidebar — per-type config forms (prompt, model, temperature, etc.) | `editor/page.tsx` |
| `VersionHistory.tsx` | Expandable version list with restore button | `editor/page.tsx` |

#### Lib — `frontend/src/lib/`

| File | Purpose | Used By |
|---|---|---|
| `api.ts` | Axios client with JWT interceptors + 401 redirect. Exports: `authApi`, `workflowApi`, `executionApi`, `workspaceApi` | All pages, `workflow-store.ts` |
| `types.ts` | TypeScript interfaces: `User`, `Workspace`, `Workflow`, `DAGNode`, `DAGEdge`, `Execution`, `ValidationResult`, `TokenResponse` | All pages, store, API client |
| `useExecutionWebSocket.ts` | React hook — WebSocket connection, auto-reconnect, HITL approval sender | `editor/page.tsx`, `executions/page.tsx` |

#### State — `frontend/src/stores/`

| File | Purpose | Used By |
|---|---|---|
| `workflow-store.ts` | Zustand store — DAG state, save/load/buildDagJson, workspace context | `editor/page.tsx`, `page.tsx` (dashboard) |

#### Tests — `frontend/tests/`

| File | Tests | Covers |
|---|---|---|
| `e2e.spec.ts` | 18 Playwright tests | Health, auth flow, editor, node adding, validation, navigation, API CRUD |

#### Config

| File | Purpose |
|---|---|
| `playwright.config.ts` | Playwright E2E config — Chromium, auto-start dev server |
| `tsconfig.json` | TypeScript config with `@/*` path alias |
| `eslint.config.mjs` | ESLint with next/core-web-vitals |
| `postcss.config.mjs` | PostCSS with Tailwind |
| `package.json` | Dependencies: next, react, @xyflow/react, zustand, axios, lucide-react, @playwright/test |

---

### Templates — `templates/`

| File | Templates | Agent Config |
|---|---|---|
| `text-summarizer.yaml` | Text summarizer with key points | gpt-4o-mini, temp 0.2 |
| `intent-classifier.yaml` | Intent classification with confidence | gpt-4o-mini, temp 0.1 |
| `collection.yaml` | 8 templates: data-extractor, sentiment-analyzer, translator, code-reviewer, content-writer, qa-answerer, json-validator, email-drafter, research-synthesizer | Various models |

---

### CI/CD — `.github/`

| File | Purpose |
|---|---|
| `workflows/ci.yml` | GitHub Actions — backend (lint + type-check + test with PostgreSQL), frontend (lint + type-check + build) |

---

## Connection Map (Who Calls Who)

### Request Flow: User Creates & Runs a Workflow

```
1. User logs in at /login
   → login/page.tsx calls authApi.login()
   → POST /api/v1/auth/login
   → auth.py validates credentials via security.py
   → Returns JWT tokens → stored in localStorage

2. User creates a workspace at /workspaces
   → workspaces/page.tsx calls workspaceApi.create()
   → POST /api/v1/workspaces
   → workspaces.py creates Workspace + WorkspaceMember (owner)

3. User opens editor at /editor
   → editor/page.tsx loads DAGCanvas + NodeToolbar + NodeConfigPanel
   → Zustand workflow-store.ts manages canvas state

4. User adds nodes (Agent, Tool, Router) via NodeToolbar
   → workflow-store.addNode() updates state

5. User connects nodes by dragging edges
   → DAGCanvas.tsx (React Flow) → workflow-store.setEdges()

6. User clicks Validate
   → editor/page.tsx calls workflowApi.validate()
   → POST /api/v1/workflows/{id}/validate
   → workflows.py calls engine/validator.py (DAGValidator)
   → Returns errors/warnings

7. User clicks Save (Ctrl+S)
   → editor/page.tsx calls workflow-store.saveWorkflow()
   → POST /api/v1/workflows (create) or PUT /api/v1/workflows/{id} (update)
   → workflows.py persists Workflow with dag_json

8. User clicks Run
   → editor/page.tsx calls executionApi.trigger()
   → POST /api/v1/executions/workflows/{id}/execute
   → executions.py creates Execution record, enqueues to Redis

9. Worker picks up job
   → workers/execution_worker.py:
     a. Loads Workflow from PostgreSQL
     b. Calls engine/compiler.py (WorkflowCompiler.compile())
     c. LangGraph StateGraph executes nodes via engine/executors.py
     d. AgentNodeExecutor calls engine/llm_client.py (call_llm())
     e. ToolNodeExecutor calls mcp/client.py (call_mcp_tool())
     f. Budget checked via services/budget.py
     g. Results persisted to Execution + ExecutionNode + CostRecord
     h. Traces sent to services/tracing.py + services/langfuse_integration.py

10. Frontend receives real-time events
    → useExecutionWebSocket.ts connects to ws://localhost:8000/ws/executions/{id}
    → main.py ConnectionManager broadcasts events
    → exec history page updates live

11. User views execution history at /executions?workflow_id=...
    → executions/page.tsx calls executionApi.list() + executionApi.trace()
    → GET /api/v1/executions/workflows/{id}/executions
    → GET /api/v1/executions/{run_id}/trace
```

### Dependency Graph (Backend Module Imports)

```
main.py
├── api/v1/router.py
│   ├── auth.py ────────── core/deps.py ──── core/security.py
│   │                                     └── core/database.py
│   ├── oauth.py ───────── core/security.py
│   │                    └ models/user.py, workspace.py
│   ├── workspaces.py ─── core/deps.py
│   │                   └ models/workspace.py
│   ├── workflows.py ──── core/deps.py
│   │                  └ engine/validator.py
│   │                  └ models/workflow.py
│   ├── executions.py ─── core/deps.py
│   │                  └ models/execution.py, workflow.py
│   ├── templates.py ──── core/deps.py
│   │                  └ models/misc.py (AgentTemplate)
│   ├── mcp_servers.py ── core/deps.py
│   │                  └ models/misc.py (MCPServer)
│   ├── costs.py ──────── core/deps.py
│   │                  └ models/misc.py (CostRecord)
│   ├── webhooks.py ───── core/deps.py
│   │                  └ models/misc.py (WebhookTrigger)
│   └── api_keys.py ───── core/deps.py
│                       └ models/api_key.py
├── core/config.py (get_settings)
├── core/rate_limit.py (RateLimitMiddleware)
├── core/security_middleware.py (SecurityHeadersMiddleware)
├── services/tracing.py (setup_tracing)
└── services/langfuse_integration.py (get_langfuse, flush)

workers/execution_worker.py
├── engine/compiler.py ──── engine/executors.py ──── engine/llm_client.py
│                          └── mcp/client.py
├── engine/checkpointer.py
├── services/budget.py
├── services/tracing.py
├── services/langfuse_integration.py
├── services/webhook_delivery.py
└── core/database.py
```

### Database Schema (ERD Summary)

```
users ─────────┬──→ workspaces (owner_id)
               │       ├──→ workspace_members (workspace_id, user_id)
               │       ├──→ workflows (workspace_id)
               │       │       ├──→ workflow_versions (workflow_id)
               │       │       ├──→ executions (workflow_id, triggered_by)
               │       │       │       ├──→ execution_nodes (execution_id)
               │       │       │       └──→ cost_records (execution_id, workflow_id, workspace_id)
               │       │       ├──→ webhook_triggers (workflow_id)
               │       │       └──→ agent_memories (workflow_id, workspace_id)
               │       ├──→ mcp_servers (workspace_id)
               │       ├──→ api_keys (workspace_id, created_by)
               │       └──→ agent_templates (author_id)
               ├──→ audit_logs (workspace_id, user_id)
               └──→ (referenced by: executions.triggered_by, workflows.created_by, etc.)
```

---

## Docker Compose Services

| Service | Image/Build | Port | Depends On | Purpose |
|---|---|---|---|---|
| `api` | `./backend/Dockerfile` | 8000 | postgres, redis | FastAPI REST + WebSocket |
| `worker` | `./backend/Dockerfile` (different cmd) | — | postgres, redis | Background execution worker |
| `frontend` | `./frontend/Dockerfile` | 3000 | api | Next.js dev server |
| `postgres` | `postgres:16-alpine` | 5432 | — | Primary database (13 tables) |
| `redis` | `redis:7-alpine` | 6379 | — | Task queue + HITL store |
| `minio` | `minio/minio:latest` | 9000, 9001 | — | S3-compatible file storage |
| `langfuse` | `langfuse/langfuse:2` | 3001 | postgres | LLM observability dashboard |
