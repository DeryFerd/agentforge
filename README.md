# AgentForge

> Open-Source Multi-Agent Workflow Orchestrator

Design agent workflows visually. Run them reliably. Monitor everything.

AgentForge is a self-hosted platform that enables developers and teams to visually design, deploy, execute, and monitor multi-agent AI workflows through a drag-and-drop DAG editor, real-time execution tracing, cost tracking, and a marketplace for reusable agent templates.

---

## Features

- **Visual DAG Editor** — Drag-and-drop canvas for composing multi-agent workflows with 7 node types (Agent, Tool, Router, Evaluator, Human-in-the-Loop, Input, Output)
- **LangGraph-Powered Execution** — Workflows compile to LangGraph state graphs for reliable, stateful execution with checkpointing
- **Real-Time Monitoring** — Watch execution animate on the DAG canvas with live node status, data flow, and timing
- **Cost Tracking** — Per-node token counting, per-workflow cost aggregation, and budget alerts
- **Agent Template Registry** — Browse, install, and publish reusable agent templates
- **MCP Server Integration** — Connect any MCP server as a tool for your agents
- **API & Webhook Triggers** — Expose workflows as REST endpoints or trigger via webhooks
- **RBAC** — Team workspaces with role-based access control (Owner, Admin, Editor, Viewer)

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, React 18, TypeScript, Tailwind CSS, React Flow |
| Backend | FastAPI, Python 3.12, SQLAlchemy 2.0, Alembic |
| Agent Framework | LangGraph |
| Protocols | MCP (Model Context Protocol) |
| Database | PostgreSQL 16 |
| Cache/Queue | Redis 7 |
| Storage | MinIO (S3-compatible) |
| Observability | OpenTelemetry, Langfuse |
| Deployment | Docker Compose |

## Quick Start

### Prerequisites

- Docker Engine 24+ and Docker Compose v2
- 8 GB RAM minimum
- (Optional) LLM API keys for OpenAI, Anthropic, or Google

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/DeryFerd/agentforge.git
cd agentforge

# 2. Copy environment file and add your API keys
cp .env.example .env
# Edit .env to add OPENAI_API_KEY or other provider keys

# 3. Start all services
docker compose up -d

# 4. Run database migrations
docker compose exec api alembic upgrade head

# 5. Open your browser
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
# Langfuse: http://localhost:3001
```

### Development Setup

```bash
# Backend
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌──────────────┐
│  Next.js    │───▶│  FastAPI     │───▶│  LangGraph   │
│  Frontend   │◀───│  API Layer   │◀───│  Engine      │
└─────────────┘    └──────┬──────┘    └──────┬───────┘
                          │                   │
                    ┌─────┴─────┐       ┌─────┴─────┐
                    │ PostgreSQL│       │   Redis    │
                    │  + MinIO  │       │  (Queue)   │
                    └───────────┘       └───────────┘
```

See [STRUCTURE.md](STRUCTURE.md) for the complete file-by-file architecture map.

## Documentation

| Document | Description |
|---|---|
| [PRD.md](PRD.md) | Product Requirements Document |
| [system-design.md](system-design.md) | Technical Architecture |
| [STRUCTURE.md](STRUCTURE.md) | Complete file structure + connection map |
| [agents.md](agents.md) | Agent Behavior & Execution Model |
| [plan.md](plan.md) | Implementation Plan |

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[Apache License 2.0](LICENSE)

## Roadmap

See [plan.md](plan.md) for the current implementation plan and post-MVP roadmap.

---

**Built for the AI orchestration era.** AgentForge demonstrates mastery of multi-agent patterns, production engineering, and developer experience — all in one open-source platform.
