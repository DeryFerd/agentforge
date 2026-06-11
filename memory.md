# AgentForge — Work Memory

> Running journal of decisions, progress, and context for this project.
> Last updated: June 11, 2026

---

## Project Overview

**AgentForge** is an open-source multi-agent workflow orchestrator platform. It provides a visual DAG editor (React Flow), a LangGraph-powered execution engine, cost tracking, RBAC, MCP tool integration, and a template marketplace — all deployable via Docker Compose.

**Repo:** https://github.com/DeryFerd/agentforge
**License:** Apache 2.0
**Target:** Portfolio project for AI Engineer roles (Multi-Agent Orchestration specialization)

---

## What Has Been Done (June 11, 2026)

### Research Phase
- Researched multi-agent orchestration trends for 2026 (1,445% adoption surge, 57% orgs in production)
- Analyzed job descriptions for AI Engineer / Agentic AI Engineer roles
- Identified key skills: LangGraph, MCP, A2A, RAG, cost-aware architecture, OWASP AST10
- Researched frameworks: LangGraph (dominant), CrewAI, AutoGen, Google ADK, Dify
- Selected 5 portfolio project ideas; chose **AgentForge** (Project #1) as the primary build
- All research documented in `RESEARCH-2026-MULTI-AGENT-ORCHESTRATION.md`

### Documentation Created (Before Coding)
- `PRD.md` — Full product requirements: 8 features, 4 user flows, competitive analysis, release criteria
- `system-design.md` — Technical architecture: layered diagram, DB schema, communication flows, security, deployment
- `agents.md` — Agent behavior spec: 6 node types with YAML configs, 5 communication patterns, cost model, error handling
- `plan.md` — 8-phase implementation plan with 100+ tasks and deliverables

### Phase 0: Project Initialization (Complete)
- Monorepo structure: `backend/`, `frontend/`, `docs/`, `.github/`, `templates/`
- Backend: FastAPI + SQLAlchemy + LangGraph + all dependencies in `pyproject.toml`
- Frontend: Next.js 14 + TypeScript + Tailwind CSS (via create-next-app)
- Docker Compose: 7 services (API, Worker, Frontend, PostgreSQL, Redis, MinIO, Langfuse)
- GitHub Actions CI: backend lint+test, frontend lint+build
- `.env.example`, `.gitignore`, `README.md`, `LICENSE` (Apache 2.0), `CONTRIBUTING.md`

### Phase 1: Database & Auth Foundation (Complete)
- Alembic migration: `0001_initial_schema.py` with all 12 tables (users, workspaces, workspace_members, workflows, workflow_versions, executions, execution_nodes, agent_templates, mcp_servers, cost_records, audit_logs, webhook_triggers)
- 12 SQLAlchemy ORM models
- Auth endpoints: register, login, JWT token issuance, refresh, /me
- `deps.py`: centralized auth dependencies — `get_current_user`, `RequireRole` (RBAC with hierarchy), `log_audit`
- All 8 API routers refactored to use `deps.py` instead of inline auth
- Workspace CRUD with member invite + role checking
- Audit logging utility
- 14 test cases in `test_auth.py` (register, login, /me, refresh, health)

### Phase 2: Workflow CRUD & DAG Editor (Complete)
- `DAGValidator` engine: Kahn's algorithm for cycle detection, orphan node detection, node type validation, config checks
- Workflow API: full CRUD + validate + export (JSON/YAML) + validated import
- Frontend: installed `@xyflow/react`, `zustand`, `axios`, `lucide-react`, `clsx`
- TypeScript types: `types.ts` with all API entity interfaces
- API client: `api.ts` with axios interceptors for JWT + 401 handling
- Zustand store: `workflow-store.ts` managing DAG state, node operations, validation
- Custom React Flow node: `AgentForgeNode.tsx` with 7 types (color-coded, icon per type)
- Node toolbar: `NodeToolbar.tsx` to add any of 7 node types
- DAG canvas: `DAGCanvas.tsx` with minimap, controls, snap-to-grid, animated edges
- Editor page: top bar (back, validate, save, run), canvas, validation bar, delete button
- Dashboard page: stats cards, empty state, quick start guide, prerequisites

### Phase 3: Execution Engine (Complete)
- `WorkflowCompiler`: transforms DAG JSON → LangGraph `StateGraph` with node functions, conditional routing, entry/exit points
- `WorkflowState` TypedDict: run_id, node_results, tokens, cost tracking
- 7 node executors:
  - **AgentNodeExecutor**: LLM call with system prompt + upstream context, echo fallback for dev
  - **ToolNodeExecutor**: Stub with template resolution (full MCP in Phase 6)
  - **RouterNodeExecutor**: Conditional routing with expression evaluation
  - **EvaluatorNodeExecutor**: Schema validation stub (LLM-as-judge deferred)
  - **HITLNodeExecutor**: Auto-approve for MVP (full human review deferred)
  - **InputNodeExecutor**: Passes workflow input data through
  - **OutputNodeExecutor**: Collects upstream outputs as final result
- Execution worker: Redis BLPOP loop → load workflow → compile → execute → persist results + per-node records
- Execution API: trigger endpoint enqueues job to Redis `agentforge:executions` queue

### Phases 4–8 (API Scaffolded, UI Deferred)
- Cost tracking: API endpoints for dashboard, per-workflow, per-execution costs
- Template registry: CRUD API with search
- MCP servers: CRUD API with health check stub
- Webhooks: trigger endpoint, webhook model
- Docker Compose + README serve as deployment docs

### Repo Published
- Created via `gh repo create` at https://github.com/DeryFerd/agentforge
- Default branch: `main`
- 86 files, 2 commits pushed

---

## Architecture Decisions Made

| Decision | Rationale |
|---|---|
| **LangGraph as core engine** | Most production-proven, graph-based, built-in checkpointing |
| **FastAPI over Django** | Async-native, auto OpenAPI spec, Pydantic integration |
| **PostgreSQL over MongoDB** | Relational model fits workflow→execution→node hierarchy, JSONB for flexible DAG |
| **React Flow for DAG editor** | Industry standard for visual graph editors, extensible custom nodes |
| **Redis for queue + pub/sub** | Single dependency for task queue and event distribution |
| **Langfuse for observability** | Purpose-built for LLM tracing, self-hostable, OpenTelemetry support |
| **Apache 2.0 license** | Permissive, encourages enterprise adoption |
| **Docker Compose for MVP** | Single-command deployment, clear upgrade path to Kubernetes |
| **deps.py centralized auth** | Single source of truth for auth/RBAC/audit, clean dependency injection |
| **Echo fallback for agent executor** | Enables development without LLM API keys |

---

## Known Gaps & Technical Debt

1. **No LangGraph PostgreSQL checkpointer** — execution state isn't persisted between nodes for crash recovery
2. **Frontend save button** doesn't actually call the backend API yet (wired up but not connected)
3. **No WebSocket real-time** — execution monitoring is polling-based, not live
4. **Tool executor is a stub** — no actual MCP server calls
5. **HITL auto-approves** — no real human review flow
6. **Evaluator is schema-only** — no LLM-as-judge
7. **No frontend auth pages** — login/register UI not built (API works)
8. **Tests only cover auth** — no integration tests for workflows, execution, or frontend
9. **No OAuth implementation** — GitHub/Google OAuth structure in config but not implemented
10. **Rate limiting not implemented** — config exists but middleware not wired

---

## Next Steps (Priority Order)

### Immediate (Make It Runnable)
1. **Wire frontend save to backend API** — connect the Save button to `PUT /workflows/:id`
2. **Add workflow loading in editor** — load existing workflow DAG into React Flow on page load
3. **Build login/register pages** — frontend forms that call auth API + store JWT
4. **Run `docker compose up` end-to-end** — verify all 7 services boot and communicate
5. **Test execution flow** — trigger a workflow via API, verify worker picks it up and runs it

### Short-Term (Production Quality)
6. **LangGraph PostgreSQL checkpointer** — enable crash recovery and execution replay
7. **WebSocket real-time monitoring** — push execution events to frontend for live DAG animation
8. **Node configuration panels** — right sidebar with forms for each node type (prompt editor, model selector, tool bindings)
9. **Execution history page** — list past runs, click to see trace
10. **Write integration tests** — pytest for workflow CRUD + execution + validator

### Medium-Term (Portfolio Differentiation)
11. **Implement MCP tool calls** — actual MCP client connecting to registered servers
12. **LLM provider integration** — wire AgentNodeExecutor to OpenAI/Anthropic/Google APIs
13. **Built-in agent templates** — 10 pre-configured templates (summarizer, classifier, extractor, etc.)
14. **Cost dashboard UI** — charts showing spend over time, per-workflow, per-model
15. **Budget enforcement** — pause execution when budget exceeded

### Long-Term (Post-MVP)
16. **A2A protocol support** — inter-agent communication
17. **Kubernetes Helm chart** — enterprise deployment option
18. **OAuth flows** — GitHub + Google login
19. **Dark mode**
20. **Agent memory** — long-term context across runs
21. **Demo video + Product Hunt launch**

---

## Session Notes

### Session 1 (June 11, 2026) — Full Build
- Duration: ~4 hours
- Approach: Research → Documentation → Code (all phases in one session)
- Key learning: Building documentation first (PRD, system-design, agents) made the coding phase much faster — every file had a clear purpose and spec
- Biggest time sink: npm install timeouts and PowerShell PSReadLine buffer errors with long commands
- Workaround for embedded git repo: `create-next-app` creates its own `.git`, needed to `rm -rf frontend/.git` before adding to parent repo
