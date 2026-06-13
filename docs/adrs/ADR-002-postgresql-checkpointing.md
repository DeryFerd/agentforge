# ADR-002: PostgreSQL Checkpointing over Redis for Workflow State

**Status:** Accepted
**Date:** 2026-06-11

## Context

Workflow execution state must persist across process restarts to enable crash recovery and execution replay. Two options: PostgreSQL (via LangGraph's AsyncPostgresSaver) or Redis (custom implementation).

## Options Considered

### 1. PostgreSQL Checkpointing (Selected)
- **Pros:** LangGraph provides `AsyncPostgresSaver` out of the box. Durable storage — survives restarts. Supports execution replay by loading any checkpoint. Already our primary database — no new infrastructure. Transactional consistency with execution records.
- **Cons:** Higher latency than Redis for frequent checkpoint writes. Larger storage footprint.

### 2. Redis State Store
- **Pros:** Lower latency for checkpoint writes. In-memory speed. Natural fit for ephemeral state.
- **Cons:** Ephemeral by default — requires Redis persistence configuration (AOF/RDB). Custom implementation needed (no LangGraph integration). Adds operational complexity. Data loss risk on Redis restart without persistence.

## Decision

**PostgreSQL checkpointing** via LangGraph's `AsyncPostgresSaver`. We already run PostgreSQL as our primary database. LangGraph provides the checkpointer as a first-class feature, eliminating custom implementation. Durability is guaranteed without additional configuration.

## Consequences

- Zero custom code for state persistence
- Execution replay is possible by loading any checkpoint from PostgreSQL
- Checkpoint writes add ~5ms latency per node execution (acceptable for workflows, not real-time)
- Redis is still used for the task queue and HITL polling — appropriate for ephemeral data
