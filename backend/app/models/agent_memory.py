"""Agent memory — long-term context persistence across workflow runs."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentMemory(Base):
    """Stores persistent memory for agents across workflow executions.

    Memory types:
    - "conversation": chat history with a user
    - "knowledge": facts learned from data processing
    - "preference": user preferences detected over time
    - "context": workflow-specific context that persists between runs
    """

    __tablename__ = "agent_memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workflow_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True, index=True
    )
    agent_node_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    memory_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="context"
    )  # conversation | knowledge | preference | context
    key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    importance: Mapped[float] = mapped_column(default=0.5)  # 0.0 - 1.0
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
