# AgentForge — System Design

> **Version:** 1.0
> **Status:** Draft
> **Last Updated:** June 2026

---

## 1. High-Level Architecture

AgentForge follows a layered, modular architecture inspired by microservices principles. Each layer is independently deployable and replaceable.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Next.js Web Application (React)                 │   │
│  │   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐ │   │
│  │   │ DAG      │  │ Execution│  │ Cost     │  │ Template  │ │   │
│  │   │ Editor   │  │ Monitor  │  │ Dashboard│  │ Registry  │ │   │
│  │   └──────────┘  └──────────┘  └──────────┘  └───────────┘ │   │
│  └─────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │  HTTP / WebSocket
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        API GATEWAY LAYER                            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    FastAPI Application                       │   │
│  │   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐ │   │
│  │   │ Auth     │  │ Workflow │  │ Execution│  │ Template  │ │   │
│  │   │ Service  │  │ Service  │  │ Service  │  │ Service   │ │   │
│  │   └──────────┘  └──────────┘  └──────────┘  └───────────┘ │   │
│  │   ┌──────────┐  ┌──────────┐  ┌──────────┐               │   │
│  │   │ Cost     │  │ MCP      │  │ Webhook  │               │   │
│  │   │ Service  │  │ Registry │  │ Service  │               │   │
│  │   └──────────┘  └──────────┘  └──────────┘               │   │
│  └─────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATION ENGINE                            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              LangGraph Runtime + Custom Executor             │   │
│  │   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐ │   │
│  │   │ Workflow │  │ State    │  │ Node     │  │ Error     │ │   │
│  │   │ Compiler │  │ Manager  │  │ Executor │  │ Recovery  │ │   │
│  │   └──────────┘  └──────────┘  └──────────┘  └───────────┘ │   │
│  └─────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       AGENT RUNTIME LAYER                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │
│  │ Agent       │  │ Agent       │  │ Agent       │   ...           │
│  │ Sandbox 1   │  │ Sandbox 2   │  │ Sandbox 3   │                │
│  │ (Container) │  │ (Container) │  │ (Container) │                │
│  └─────────────┘  └─────────────┘  └─────────────┘                │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     DATA & INFRASTRUCTURE                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │PostgreSQL│  │  Redis   │  │  MinIO/  │  │ OpenTelemetry     │  │
│  │(State,   │  │(Queue,   │  │  S3      │  │ (Traces, Metrics, │  │
│  │ Config)  │  │ Cache)   │  │(Files)   │  │  Logs)            │  │
│  └──────────┘  └──────────┘  └──────────┘  └───────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Breakdown

### 2.1 Frontend — Next.js Web Application

**Technology:** Next.js 14+ (App Router), React 18+, TypeScript, Tailwind CSS, React Flow (DAG editor)

**Key Modules:**

| Module | Responsibility | Key Libraries |
|---|---|---|
| **DAG Editor** | Visual canvas for building workflows | React Flow, custom node renderers |
| **Execution Monitor** | Real-time visualization of running workflows | WebSocket client, React Flow overlays |
| **Cost Dashboard** | Token usage and cost analytics | Recharts, date range filters |
| **Template Registry** | Browse, install, publish agent templates | Search, categories, detail views |
| **Auth & Settings** | Login, workspace management, RBAC UI | NextAuth.js, role-based navigation |
| **API Explorer** | Test workflow API endpoints from the UI | Swagger-like interface |

**State Management:**
- Local state: Zustand (lightweight, no boilerplate)
- Server state: TanStack Query (React Query) for API caching and mutations
- Real-time: Native WebSocket for execution streaming

**DAG Editor Details:**
- Custom node types mapped to AgentForge node types (Agent, Tool, Router, Evaluator, HITL, I/O)
- Node configuration panel (right sidebar) opens on node click
- Canvas features: pan, zoom, minimap, snap-to-grid, auto-layout
- Validation overlay: highlights invalid connections, missing required fields
- Export/import: workflow JSON, YAML

### 2.2 API Layer — FastAPI Application

**Technology:** FastAPI, Python 3.12+, Pydantic v2, SQLAlchemy 2.0, Alembic

**Service Modules:**

| Service | Responsibility |
|---|---|
| **Auth Service** | JWT issuance, OAuth flows (GitHub, Google), password hashing, session management |
| **Workflow Service** | CRUD for workflows, versioning, validation, compilation to LangGraph |
| **Execution Service** | Trigger workflow runs, manage execution state, stream events via WebSocket |
| **Template Service** | CRUD for templates, versioning, community submission, review workflow |
| **Cost Service** | Aggregate token usage from execution events, calculate costs, enforce budgets |
| **MCP Registry Service** | Register/deregister MCP servers, health checks, capability discovery |
| **Webhook Service** | Manage webhook triggers, validate payloads, enqueue workflow executions |
| **RBAC Service** | Workspace membership, role assignment, permission checks per resource |

**API Design:**
- RESTful endpoints with OpenAPI spec auto-generated by FastAPI
- WebSocket endpoint: `/ws/executions/{run_id}` for real-time event streaming
- Pagination: cursor-based for executions, offset-based for workflows/templates
- Error format: structured JSON with error code, message, and details
- Rate limiting: per-user, per-workflow, configurable

**Key Endpoints:**

```
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/oauth/{provider}

GET    /api/v1/workspaces
POST   /api/v1/workspaces
GET    /api/v1/workspaces/{id}/members
PUT    /api/v1/workspaces/{id}/members/{user_id}/role

GET    /api/v1/workflows
POST   /api/v1/workflows
GET    /api/v1/workflows/{id}
PUT    /api/v1/workflows/{id}
DELETE /api/v1/workflows/{id}
POST   /api/v1/workflows/{id}/validate
POST   /api/v1/workflows/{id}/export

POST   /api/v1/workflows/{id}/execute
GET    /api/v1/workflows/{id}/executions
GET    /api/v1/executions/{run_id}
GET    /api/v1/executions/{run_id}/trace
POST   /api/v1/executions/{run_id}/cancel
POST   /api/v1/executions/{run_id}/nodes/{node_id}/retry
WS     /ws/executions/{run_id}

GET    /api/v1/templates
POST   /api/v1/templates
GET    /api/v1/templates/{id}
POST   /api/v1/templates/{id}/publish
POST   /api/v1/templates/{id}/install

GET    /api/v1/mcp-servers
POST   /api/v1/mcp-servers
DELETE /api/v1/mcp-servers/{id}
GET    /api/v1/mcp-servers/{id}/health

GET    /api/v1/costs/dashboard
GET    /api/v1/costs/workflows/{id}
GET    /api/v1/costs/executions/{run_id}
PUT    /api/v1/workflows/{id}/budget

POST   /api/v1/webhooks/{workflow_id}
GET    /api/v1/webhooks
DELETE /api/v1/webhooks/{id}
```

### 2.3 Orchestration Engine — LangGraph Runtime

**Technology:** LangGraph 0.2+, custom workflow compiler, Python

**Components:**

#### Workflow Compiler
- Takes workflow JSON (from the visual editor) as input
- Validates the DAG structure (no cycles, valid connections, type compatibility)
- Compiles into a LangGraph `StateGraph` with:
  - Nodes mapped to agent/tool/router functions
  - Edges mapped to conditional transitions
  - State schema derived from workflow input/output definitions
- Outputs a compiled `CompiledGraph` ready for execution

#### State Manager
- Manages workflow execution state
- State schema includes:
  ```python
  class WorkflowState(TypedDict):
      run_id: str
      workflow_id: str
      status: Literal["running", "paused", "completed", "failed", "cancelled"]
      current_node: str
      node_results: dict[str, NodeResult]
      global_context: dict[str, Any]
      token_usage: TokenUsage
      cost_usd: float
      started_at: datetime
      completed_at: Optional[datetime]
      error: Optional[ExecutionError]
  ```
- State persistence via PostgreSQL (LangGraph checkpointer)
- State recovery: if process crashes, execution can resume from last checkpoint

#### Node Executor
- Executes individual nodes based on their type:
  - **Agent Node:** Constructs LLM call with system prompt + context + tools → returns structured output
  - **Tool Node:** Calls registered MCP server or HTTP API → returns result
  - **Router Node:** Evaluates conditions on upstream output → returns branch selection
  - **Evaluator Node:** Runs validation logic (schema check, LLM-as-judge) → returns pass/fail + score
  - **HITL Node:** Pauses execution, emits event, waits for human input via API callback
- Each executor:
  - Logs input/output to the trace store
  - Tracks token usage (for agent nodes)
  - Enforces timeout (configurable per node)
  - Emits OpenTelemetry spans

#### Error Recovery
- Per-node retry policy: max_retries, backoff strategy (exponential), retryable error types
- Workflow-level: if a node fails after all retries, workflow enters "failed" state
- Partial retry: re-execute from a specific node (uses checkpointed state)
- Circuit breaker: if a node fails N times in M executions, auto-disable and alert

### 2.4 Agent Runtime — Sandboxed Execution

**Technology:** Docker containers (per-agent isolation), gVisor (optional hardening)

**Sandbox Model:**
- Each agent node execution runs within the orchestrator process (MVP)
- Tool calls and MCP server interactions are sandboxed:
  - Network egress restricted to registered MCP server endpoints
  - File system access limited to a temporary workspace directory
  - No access to platform internals or other workflow states
- Future: container-per-agent for stronger isolation (enterprise tier)

**Agent Execution Flow:**
```
Node Executor receives execution request
  → Constructs LLM context:
      - System prompt (from node config)
      - Global workflow state (relevant subset)
      - Upstream node outputs (from connected edges)
      - Available tools (from MCP registry)
  → Calls LLM (streaming response)
  → If LLM requests tool call:
      → Validate tool is registered and permitted
      → Execute tool via MCP client or HTTP call
      → Feed result back to LLM
      → Repeat until LLM produces final answer
  → Parse final output against node's output schema
  → Emit execution event (success/failure + output)
  → Update token counters and cost tracker
```

### 2.5 Data Layer

| Component | Technology | Purpose |
|---|---|---|
| **Primary Database** | PostgreSQL 16 | Workflow definitions, execution state, user accounts, workspace config, template metadata, cost records |
| **Cache & Queue** | Redis 7 | Execution event queue, session cache, rate limiting counters, WebSocket pub/sub |
| **File Storage** | MinIO (S3-compatible) | Uploaded files, exported workflow artifacts, template packages |
| **Observability** | OpenTelemetry + Langfuse | Distributed traces, agent execution spans, metrics, log aggregation |

**Database Schema (Core Tables):**

```
users                    — id, email, password_hash, oauth_provider, created_at
workspaces               — id, name, owner_id, plan, created_at
workspace_members        — workspace_id, user_id, role, joined_at
workflows                — id, workspace_id, name, description, dag_json, version, created_by, created_at, updated_at
workflow_versions        — id, workflow_id, version_number, dag_json, created_at
executions               — id, workflow_id, triggered_by, trigger_type, status, started_at, completed_at, error
execution_nodes          — id, execution_id, node_id, status, input_json, output_json, tokens_in, tokens_out, cost, started_at, completed_at, error
agent_templates          — id, name, description, category, system_prompt, model_config, tool_bindings, version, author_id, is_verified, download_count, created_at
mcp_servers              — id, workspace_id, name, url, auth_config, capabilities_json, health_status, last_check_at
webhook_triggers         — id, workflow_id, secret, is_active, created_at
cost_records             — id, execution_id, workflow_id, workspace_id, node_id, model, tokens_in, tokens_out, cost_usd, recorded_at
audit_logs               — id, workspace_id, user_id, action, resource_type, resource_id, details_json, created_at
```

---

## 3. Communication & Data Flow

### 3.1 Synchronous (REST API)
```
Client → FastAPI → Service Layer → PostgreSQL
Client ← FastAPI ← Service Layer ← PostgreSQL
```

### 3.2 Asynchronous (Execution Queue)
```
Client triggers execution (POST /execute)
  → FastAPI enqueues execution job to Redis
  → Worker picks up job from Redis queue
  → Worker compiles workflow → LangGraph StateGraph
  → Worker executes graph → emits events to Redis pub/sub
  → WebSocket relay reads events from Redis → pushes to connected clients
  → Worker persists final state to PostgreSQL
```

### 3.3 Real-Time (WebSocket)
```
Client connects to ws://host/ws/executions/{run_id}
  → Server authenticates via JWT in query param or first message
  → Server subscribes client to Redis channel: execution:{run_id}:events
  → Worker emits events: node_started, node_completed, node_failed, execution_paused, execution_completed
  → Relay pushes events to WebSocket
  → Client updates DAG visualization in real-time
```

### 3.4 MCP Server Communication
```
Agent Node needs to call a tool
  → Node Executor looks up MCP server from registry
  → Creates MCP client connection (stdio or SSE transport)
  → Calls tool with validated parameters
  → Receives structured result
  → Closes connection (or reuses pooled connection)
  → Feeds result back to LLM as tool output
```

---

## 4. Security Architecture

### 4.1 Authentication
- JWT tokens (access: 15min, refresh: 7 days)
- OAuth 2.0 flows for GitHub and Google
- Password hashing: bcrypt (cost factor 12)
- API keys: generated per-workflow, hashed with SHA-256, stored as prefix + hash

### 4.2 Authorization (RBAC)
- Every API endpoint checks workspace membership and role
- Permission matrix:

| Action | Owner | Admin | Editor | Viewer |
|---|---|---|---|---|
| Manage workspace settings | Yes | No | No | No |
| Manage team members | Yes | Yes | No | No |
| Create/edit workflows | Yes | Yes | Yes | No |
| Execute workflows | Yes | Yes | Yes | No |
| View executions & costs | Yes | Yes | Yes | Yes |
| Publish templates | Yes | Yes | Yes | No |
| Manage MCP servers | Yes | Yes | No | No |
| View audit logs | Yes | Yes | No | No |

### 4.3 Agent Security (OWASP AST10)
- **Skill Authorization:** Agents can only call tools explicitly bound to their node configuration
- **Supply Chain Integrity:** Community templates undergo review before publication; signed with contributor identity
- **Runtime Isolation:** Agent execution sandboxed (no access to platform DB, no arbitrary network calls)
- **Input Validation:** All workflow inputs validated against schema before execution
- **Secret Management:** API keys, MCP auth credentials stored encrypted (AES-256-GCM) using a master key from environment

### 4.4 Data Security
- TLS 1.3 for all client-server communication
- PostgreSQL row-level security for workspace data isolation
- Encrypted at rest: database (PostgreSQL TDE), file storage (MinIO encryption)
- Audit logging: all mutations logged with user, timestamp, and resource details

---

## 5. Deployment Architecture

### 5.1 MVP Deployment (Docker Compose)

```yaml
services:
  frontend:       # Next.js app (port 3000)
  api:            # FastAPI app (port 8000)
  worker:         # LangGraph execution worker (background)
  websocket-relay:# WebSocket event relay (port 8001)
  postgres:       # PostgreSQL 16 (port 5432)
  redis:          # Redis 7 (port 6379)
  minio:          # MinIO file storage (port 9000)
  langfuse:       # Langfuse observability (port 3001)
```

**Resource Requirements (Minimum):**
- CPU: 4 cores
- RAM: 8 GB
- Storage: 20 GB SSD
- Docker Engine 24+ and Docker Compose v2

### 5.2 Production Deployment (Future)
- Kubernetes with Helm chart
- Horizontal pod autoscaling for API and Worker
- Managed PostgreSQL (RDS/Cloud SQL)
- Managed Redis (ElastiCache/Memorystore)
- CDN for frontend static assets
- Load balancer with SSL termination

---

## 6. Observability Stack

### 6.1 Tracing
- OpenTelemetry SDK instrumented in all services
- Span hierarchy: Workflow Run → Node Execution → LLM Call → Tool Call
- Exported to Langfuse (self-hosted) for visualization
- Each span includes: input/output, token counts, model used, latency, cost

### 6.2 Metrics
- **Business metrics:** Active workflows, executions per day, templates published, templates installed
- **Performance metrics:** Compilation latency, execution latency (p50, p95, p99), WebSocket connection count
- **Cost metrics:** Token usage per model, cost per workflow, cost per workspace, budget alert triggers
- **Reliability metrics:** Execution success rate, node failure rate, retry rate, MCP server error rate

### 6.3 Logging
- Structured JSON logs (Python `structlog`)
- Log levels: DEBUG (development), INFO (production), WARNING (degradation), ERROR (failures)
- Correlation ID (run_id) propagated through all logs for trace-based debugging
- Log aggregation via Langfuse or stdout → container log driver

---

## 7. Technology Stack Summary

| Layer | Technology | Version |
|---|---|---|
| Frontend Framework | Next.js (App Router) | 14+ |
| UI Components | React + Tailwind CSS + shadcn/ui | 18+ |
| DAG Editor | React Flow | 11+ |
| Charts | Recharts | 2+ |
| Backend Framework | FastAPI | 0.110+ |
| ORM | SQLAlchemy | 2.0+ |
| Migrations | Alembic | 1.13+ |
| Validation | Pydantic | 2+ |
| Task Queue | Redis + custom worker | 7+ |
| Agent Framework | LangGraph | 0.2+ |
| LLM Providers | OpenAI, Anthropic, Google | Latest APIs |
| MCP Client | `mcp` Python SDK | Latest |
| Database | PostgreSQL | 16 |
| Cache/Queue | Redis | 7 |
| File Storage | MinIO | Latest |
| Observability | OpenTelemetry + Langfuse | Latest |
| Auth | python-jose (JWT) + httpx (OAuth) | Latest |
| Containerization | Docker + Docker Compose | 24+ |
| CI/CD | GitHub Actions | N/A |

---

## 8. Key Design Decisions

| Decision | Rationale |
|---|---|
| **LangGraph as orchestration core** | Most production-proven agent framework; graph-based architecture maps naturally to DAG workflows; built-in checkpointing |
| **PostgreSQL over MongoDB** | Strong relational model fits workflow→execution→node hierarchy; built-in JSON support for flexible DAG storage; row-level security for multi-tenancy |
| **Redis for queue + pub/sub** | Single dependency for both task queue and real-time event distribution; battle-tested at scale |
| **React Flow for DAG editor** | Industry standard for visual graph editors; extensible custom nodes; active community |
| **FastAPI over Django/Flask** | Async-native; automatic OpenAPI spec; Pydantic integration; performance comparable to Go for I/O-bound workloads |
| **Langfuse over custom observability** | Purpose-built for LLM tracing; self-hostable; supports OpenTelemetry; saves months of building custom dashboards |
| **Docker Compose for MVP** | Single-command deployment; sufficient for small teams; clear upgrade path to Kubernetes |
| **Apache 2.0 license** | Permissive; encourages enterprise adoption and contribution; no copyleft friction |
