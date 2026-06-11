# AgentForge — Implementation Plan (End-to-End)

> **Version:** 1.0
> **Status:** Active
> **Last Updated:** June 2026
> **Estimated Duration:** 10–14 weeks for MVP

---

## Overview

This plan covers the full implementation of AgentForge from project initialization to a deployed, usable MVP. The plan is divided into **8 phases**, each building on the previous. Every phase ends with a verifiable milestone.

**Goal:** Ship a self-hosted, open-source multi-agent workflow orchestrator that real developers can install and use.

---

## Phase 0: Project Initialization & Infrastructure
**Duration:** 3–4 days
**Milestone:** Project scaffolded, CI/CD running, development environment ready

### Tasks

| # | Task | Deliverable |
|---|---|---|
| 0.1 | Initialize monorepo structure (backend + frontend + docker) | Repository with clear directory layout |
| 0.2 | Set up GitHub repository with README, LICENSE (Apache 2.0), CONTRIBUTING.md | Public GitHub repo |
| 0.3 | Initialize backend: FastAPI project with Alembic, SQLAlchemy, Pydantic | Bootable API server |
| 0.4 | Initialize frontend: Next.js 14 (App Router) + Tailwind + shadcn/ui | Bootable web app |
| 0.5 | Create Docker Compose with PostgreSQL, Redis, MinIO, Langfuse | `docker compose up` starts all services |
| 0.6 | Set up GitHub Actions CI: lint, type-check, test, build | CI pipeline green on every push |
| 0.7 | Configure development tooling: ruff, mypy, eslint, prettier, pre-commit hooks | Consistent code quality |
| 0.8 | Create `.env.example` with all required environment variables | Documented configuration |
| 0.9 | Write initial README with installation instructions and architecture overview | Developer onboarding doc |

### Directory Structure
```
agentforge/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI routers
│   │   ├── core/          # Config, security, dependencies
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic
│   │   ├── engine/        # LangGraph orchestration engine
│   │   ├── mcp/           # MCP client integration
│   │   └── workers/       # Background execution workers
│   ├── alembic/           # Database migrations
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/           # Next.js App Router pages
│   │   ├── components/    # React components
│   │   ├── lib/           # Utilities, API client
│   │   ├── stores/        # Zustand stores
│   │   └── types/         # TypeScript types
│   ├── package.json
│   └── Dockerfile
├── templates/             # Built-in agent templates
├── docker-compose.yml
├── docker-compose.dev.yml
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── release.yml
├── docs/
├── LICENSE
├── CONTRIBUTING.md
└── README.md
```

---

## Phase 1: Database & Auth Foundation
**Duration:** 5–7 days
**Milestone:** User can register, log in, create workspace; database schema migrated

### Tasks

| # | Task | Deliverable |
|---|---|---|
| 1.1 | Design and implement Alembic migrations for all core tables (users, workspaces, workspace_members, workflows, executions, execution_nodes, templates, mcp_servers, cost_records, audit_logs) | Migration files, all tables created |
| 1.2 | Implement SQLAlchemy models for all tables | ORM models with relationships |
| 1.3 | Implement Auth Service: register, login, JWT issuance, token refresh | Working auth endpoints |
| 1.4 | Implement OAuth flows: GitHub and Google (using httpx) | OAuth login working |
| 1.5 | Implement Workspace Service: create workspace, invite members, manage roles | Workspace CRUD + RBAC |
| 1.6 | Implement RBAC middleware: permission checks per endpoint | All endpoints protected |
| 1.7 | Implement Audit Log Service: auto-log all mutations | Audit trail for all actions |
| 1.8 | Build frontend auth pages: login, register, OAuth buttons | Auth UI complete |
| 1.9 | Build frontend workspace setup: create workspace, invite members, role management | Workspace UI complete |
| 1.10 | Write tests for auth + RBAC (unit + integration) | >80% coverage on auth module |

---

## Phase 2: Workflow CRUD & DAG Editor
**Duration:** 10–14 days
**Milestone:** User can create, edit, save, and validate workflows via the visual DAG editor

### Tasks

| # | Task | Deliverable |
|---|---|---|
| 2.1 | Implement Workflow Service: CRUD, versioning (simple), validation | API endpoints for workflows |
| 2.2 | Design workflow JSON schema (DAG representation) | Documented schema |
| 2.3 | Implement workflow validation: cycle detection, orphan nodes, connection validity, schema compatibility | Validation endpoint with clear error messages |
| 2.4 | Implement workflow import/export (JSON, YAML) | Export/import endpoints |
| 2.5 | Set up React Flow in frontend with custom node types | DAG editor canvas rendering |
| 2.6 | Build custom node renderers: Agent, Tool, Router, Evaluator, HITL, Input, Output | All 7 node types visual |
| 2.7 | Build node configuration panel (right sidebar) | Click node → config form opens |
| 2.8 | Build Agent Node config: prompt editor, model selector, tool bindings, output schema editor | Agent config UI functional |
| 2.9 | Build Router Node config: condition builder, routing mode selector | Router config UI functional |
| 2.10 | Build Evaluator Node config: criteria editor, threshold slider, mode selector | Evaluator config UI functional |
| 2.11 | Build edge connections: drag to connect, validation on connection, delete edge | Edge interaction working |
| 2.12 | Build canvas features: pan, zoom, minimap, auto-layout, snap-to-grid | Smooth DAG editing UX |
| 2.13 | Build workflow list page (dashboard): search, filter, sort, duplicate, delete | Workflow management UI |
| 2.14 | Implement workflow save (auto-save + manual save with Ctrl+S) | Persistent workflow storage |
| 2.15 | Build workflow validation UI: show errors/warnings on canvas before execution | Visual validation feedback |
| 2.16 | Write tests for workflow CRUD + validation | >80% coverage |

---

## Phase 3: Execution Engine (Core Orchestration)
**Duration:** 14–18 days
**Milestone:** User can execute a workflow and see results; engine supports all node types

### Tasks

| # | Task | Deliverable |
|---|---|---|
| 3.1 | Implement Workflow Compiler: DAG JSON → LangGraph StateGraph | Compiler module |
| 3.2 | Implement WorkflowState schema (TypedDict) | State definition |
| 3.3 | Implement LangGraph checkpointer (PostgreSQL-backed) | State persistence |
| 3.4 | Implement Redis task queue for execution jobs | Queue infrastructure |
| 3.5 | Implement execution worker: picks up jobs, compiles, runs graphs | Worker process |
| 3.6 | Implement Agent Node Executor: context assembly, LLM call, tool loop, output validation | Agent execution working |
| 3.7 | Implement Tool Node Executor: input resolution, MCP call, output mapping | Tool execution working |
| 3.8 | Implement Router Node Executor: conditional evaluation, LLM-based routing, fan-out | Routing working |
| 3.9 | Implement Evaluator Node Executor: schema validation, LLM-as-judge, custom function | Evaluation working |
| 3.10 | Implement HITL Node Executor: pause, notify, wait, resume | Human-in-the-loop working |
| 3.11 | Implement Input/Output Node executors | Workflow I/O working |
| 3.12 | Implement parallel execution (fan-out/fan-in) with asyncio | Concurrent branches |
| 3.13 | Implement error recovery: retry policies, exponential backoff, on_fail actions | Graceful failure handling |
| 3.14 | Implement execution record persistence: create, update, query executions | Execution history in DB |
| 3.15 | Implement execution API: trigger run, get status, cancel, retry node | Execution endpoints live |
| 3.16 | Implement basic execution UI: run button, status indicator, output viewer | Can run workflow and see result |
| 3.17 | Write tests for compiler + all executors (unit + integration with mock LLM) | >80% coverage on engine |

---

## Phase 4: Real-Time Monitoring & Observability
**Duration:** 7–10 days
**Milestone:** User can watch workflow execution in real-time on the DAG canvas; full tracing available

### Tasks

| # | Task | Deliverable |
|---|---|---|
| 4.1 | Implement execution event system: emit events at each node lifecycle stage | Event emitter module |
| 4.2 | Set up Redis pub/sub for execution events | Event distribution |
| 4.3 | Implement WebSocket endpoint: auth, subscribe to run events, push to clients | WebSocket server |
| 4.4 | Build WebSocket relay service: reads Redis events → pushes to WebSocket clients | Relay process |
| 4.5 | Build frontend WebSocket client: connect, reconnect, event parsing | Real-time data in browser |
| 4.6 | Build real-time DAG visualization: nodes light up (running/green/red/yellow) | Animated execution on canvas |
| 4.7 | Build execution timeline panel: per-node timing, tokens, cost | Timeline sidebar |
| 4.8 | Build node inspector: click node → see input, output, LLM prompt, tool calls, error | Detailed node inspection |
| 4.9 | Build execution history page: list runs, filter by status, view details | Execution log browser |
| 4.10 | Implement OpenTelemetry instrumentation: spans for workflow → node → LLM → tool | Distributed traces |
| 4.11 | Integrate Langfuse: export traces, configure project, build dashboards | Langfuse receiving data |
| 4.12 | Implement execution replay: load past execution, step through nodes | Replay functionality |
| 4.13 | Implement "retry from node" feature: re-execute from checkpointed state | Partial retry working |
| 4.14 | Write tests for WebSocket + event system | Event system tested |

---

## Phase 5: Cost Tracking & Budget Management
**Duration:** 5–7 days
**Milestone:** Every execution shows token usage and cost; budgets enforce limits

### Tasks

| # | Task | Deliverable |
|---|---|---|
| 5.1 | Implement token counter: track input/output tokens per LLM call | Token counting in executors |
| 5.2 | Implement model pricing table: store and update pricing per model | Pricing data |
| 5.3 | Implement cost calculator: compute cost per node, per execution, per workflow | Cost computation |
| 5.4 | Persist cost records to database after each execution | Cost data in DB |
| 5.5 | Build cost dashboard: total spend over time, per-workflow, per-model | Cost visualization |
| 5.6 | Implement budget configuration: per-run, per-workflow, per-workspace limits | Budget settings |
| 5.7 | Implement budget enforcement: check before execution, pause on breach | Budget guards |
| 5.8 | Implement budget alerts: email/Slack notification when threshold reached | Alert delivery |
| 5.9 | Build cost breakdown in execution view: which node was most expensive | Per-node cost display |
| 5.10 | Implement cost optimization suggestions: model routing recommendations | Optimization hints |
| 5.11 | Write tests for cost tracking + budget enforcement | Cost module tested |

---

## Phase 6: MCP Integration & Template Registry
**Duration:** 7–10 days
**Milestone:** Users can register MCP servers and use them as tools; templates are browsable and installable

### Tasks

| # | Task | Deliverable |
|---|---|---|
| 6.1 | Implement MCP Registry Service: register, deregister, list MCP servers | MCP server management API |
| 6.2 | Implement MCP client wrapper: connect to server, discover capabilities, call tools | MCP tool calling |
| 6.3 | Implement MCP health checks: periodic pings, status tracking | Health monitoring |
| 6.4 | Build MCP server management UI: add server, test connection, view capabilities | MCP settings page |
| 6.5 | Integrate MCP tools into Agent Node executor: tools from registry available to LLM | Tool binding in agents |
| 6.6 | Build MCP tool selector in Agent Node config: pick tools from registered servers | Tool assignment UI |
| 6.7 | Implement Template Service: CRUD, versioning, search, categorization | Template API |
| 6.8 | Build 10 built-in templates (summarizer, classifier, extractor, etc.) | Pre-built templates |
| 6.9 | Build template marketplace UI: browse, search, filter, view details | Template browser |
| 6.10 | Implement template installation: install template → creates pre-configured node | Template → node creation |
| 6.11 | Implement template publishing: submit from agent node config | Publish flow |
| 6.12 | Implement template review pipeline: automated tests, manual approval | Review workflow |
| 6.13 | Write tests for MCP integration + template service | Integration tested |

---

## Phase 7: API Triggers, Webhooks & Polish
**Duration:** 7–10 days
**Milestone:** Workflows can be triggered via API/webhook; UI is polished; RBAC is complete

### Tasks

| # | Task | Deliverable |
|---|---|---|
| 7.1 | Implement workflow API triggers: each workflow gets a unique endpoint + API key | API trigger endpoints |
| 7.2 | Implement API key management: generate, rotate, revoke per workflow | API key CRUD |
| 7.3 | Implement rate limiting per API key | Rate limiting middleware |
| 7.4 | Implement Webhook Service: register webhooks, validate payloads, trigger workflows | Webhook infrastructure |
| 7.5 | Build webhook management UI: create, test, view delivery logs | Webhook settings |
| 7.6 | Build workflow execution page (final): comprehensive output view, error details | Execution result page |
| 7.7 | Build onboarding flow: first-time wizard, create workflow from template | Onboarding experience |
| 7.8 | Polish DAG editor UX: keyboard shortcuts, undo/redo, copy/paste nodes | Smooth editing |
| 7.9 | Build dashboard home page: workflow stats, recent executions, cost summary | Dashboard overview |
| 7.10 | Implement responsive design: mobile-friendly for monitoring (not editing) | Mobile monitoring |
| 7.11 | Add loading states, error boundaries, toast notifications throughout | Professional UX |
| 7.12 | Write E2E tests: create workflow → execute → view results (Playwright) | E2E test suite |
| 7.13 | Security audit: OWASP AST10 checklist, penetration test, fix vulnerabilities | Security review passed |
| 7.14 | Performance optimization: query optimization, caching, lazy loading | Sub-second page loads |

---

## Phase 8: Deployment, Documentation & Launch
**Duration:** 5–7 days
**Milestone:** AgentForge is deployed, documented, and publicly available

### Tasks

| # | Task | Deliverable |
|---|---|---|
| 8.1 | Finalize Docker Compose: production-ready config, health checks, restart policies | `docker compose up` works cleanly |
| 8.2 | Create Docker Compose dev variant with hot-reload and debug tools | Developer-friendly setup |
| 8.3 | Write installation guide: prerequisites, step-by-step setup, troubleshooting | Installation docs |
| 8.4 | Write quickstart guide: "Build your first workflow in 10 minutes" | Quickstart tutorial |
| 8.5 | Write architecture documentation: system overview, component diagram, data flow | Architecture docs |
| 8.6 | Write API reference: auto-generated from OpenAPI spec, hosted at /docs | API documentation |
| 8.7 | Write agent template guide: how to use, how to create, how to publish | Template docs |
| 8.8 | Write CONTRIBUTING.md: development setup, coding standards, PR process | Contributor guide |
| 8.9 | Record demo video: 3-minute walkthrough of key features | YouTube/Loom video |
| 8.10 | Set up GitHub Discussions for community support | Community channel |
| 8.11 | Tag "good first issue" on 5–10 beginner-friendly issues | Contributor onboarding |
| 8.12 | Deploy demo instance: public URL where people can try AgentForge | Live demo at agentforge.dev (or similar) |
| 8.13 | Publish launch post: blog post, Reddit r/MachineLearning, Hacker News, Twitter/X | Public launch |
| 8.14 | Submit to Product Hunt, awesome lists, and developer newsletters | Distribution |
| 8.15 | Monitor launch: respond to issues, feedback, and feature requests | Active maintenance |

---

## Timeline Summary

| Phase | Duration | Cumulative | Milestone |
|---|---|---|---|
| **Phase 0** — Init | 3–4 days | ~1 week | Project scaffolded, CI running |
| **Phase 1** — Auth & DB | 5–7 days | ~2 weeks | Auth working, schema migrated |
| **Phase 2** — DAG Editor | 10–14 days | ~4 weeks | Visual editor functional |
| **Phase 3** — Engine | 14–18 days | ~6–7 weeks | Workflows execute correctly |
| **Phase 4** — Monitoring | 7–10 days | ~8 weeks | Real-time visualization |
| **Phase 5** — Cost | 5–7 days | ~9 weeks | Cost tracking live |
| **Phase 6** — MCP & Templates | 7–10 days | ~10–11 weeks | Tools + templates working |
| **Phase 7** — Polish | 7–10 days | ~12 weeks | Production-quality UX |
| **Phase 8** — Launch | 5–7 days | ~13–14 weeks | Public release |

---

## Post-MVP Roadmap (Deferred)

After MVP launch, the following features are planned based on community feedback:

| Feature | Priority |
|---|---|
| A2A protocol support for inter-agent communication | High |
| Kubernetes Helm chart for enterprise deployment | High |
| Workflow versioning with visual diff | Medium |
| Dark mode | Medium |
| Agent memory / long-term context across runs | Medium |
| Multi-language SDK (Python, TypeScript, Go) | Medium |
| Managed cloud offering (AgentForge Cloud) | Low (initially) |
| Enterprise SSO (SAML, OIDC) | Low (initially) |

---

## Definition of Done (Per Phase)

Each phase is "done" when:
- [ ] All tasks in the phase are completed
- [ ] Unit and integration tests pass (>80% coverage for new modules)
- [ ] No critical or high-severity bugs in the phase's scope
- [ ] The milestone demo works end-to-end without errors
- [ ] Code is reviewed (self-review for solo developer)
- [ ] Documentation is updated to reflect new functionality
- [ ] CI pipeline is green
