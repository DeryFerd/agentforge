# ADR-001: LangGraph over CrewAI/AutoGen for Orchestration Engine

**Status:** Accepted
**Date:** 2026-06-11

## Context

We need an orchestration engine to compile visual DAG definitions into executable multi-agent workflows. The engine must support: conditional routing, parallel execution, state persistence, checkpointing for crash recovery, and integration with multiple LLM providers.

## Options Considered

### 1. LangGraph (Selected)
- **Pros:** Graph-based architecture maps directly to DAG workflows. Built-in checkpointing with PostgreSQL backend. First-class support for conditional edges and state machines. Production-proven at Klarna, Cisco, Vizient. Active development by LangChain team. Native async support.
- **Cons:** Steeper learning curve. Tighter coupling to LangChain ecosystem. Smaller community than AutoGen.

### 2. CrewAI
- **Pros:** Simple role-based agent definition. Good for sequential pipelines. Large community.
- **Cons:** No native graph/DAG support. No checkpointing. Sequential-only execution. Not suitable for complex conditional routing.

### 3. AutoGen (Microsoft)
- **Pros:** Strong conversational multi-agent patterns. Good for research. Backed by Microsoft.
- **Cons:** Conversation-first paradigm doesn't map to workflow DAGs. Harder to control execution flow deterministically. Less production usage.

### 4. Custom Engine
- **Pros:** Full control. No framework lock-in.
- **Cons:** Months of development. Need to build checkpointing, error recovery, state management from scratch.

## Decision

**LangGraph** was selected because its graph-based `StateGraph` is a near-1:1 mapping to our visual DAG editor. The `WorkflowCompiler` translates our DAG JSON directly into LangGraph nodes and edges, requiring minimal translation logic. Built-in PostgreSQL checkpointing (`AsyncPostgresSaver`) provides crash recovery without custom implementation.

## Consequences

- The compiler pattern (`compiler.py`) is clean — DAG nodes become LangGraph nodes, edges become LangGraph edges
- Conditional routing uses LangGraph's `add_conditional_edges` — native support
- State persistence uses LangGraph's checkpointer — no custom state management needed
- Trade-off: we're coupled to LangGraph's API. If LangGraph changes significantly, the compiler needs updating
- Mitigation: the executor abstraction (`BaseNodeExecutor`) isolates node logic from LangGraph internals
