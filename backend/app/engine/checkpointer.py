"""LangGraph PostgreSQL checkpointer for crash recovery and execution replay."""

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.core.config import get_settings

settings = get_settings()


def get_checkpointer() -> AsyncPostgresSaver:
    """Create a LangGraph PostgreSQL checkpointer.

    This enables:
    - Crash recovery: resume execution from last checkpoint
    - Execution replay: re-run from any checkpoint
    - State persistence: workflow state survives process restart
    """
    # Convert asyncpg URL to psycopg URL for LangGraph checkpointer
    db_url = settings.database_url
    if "+asyncpg" in db_url:
        db_url = db_url.replace("+asyncpg", "")

    checkpointer = AsyncPostgresSaver.from_conn_string(db_url)
    return checkpointer
