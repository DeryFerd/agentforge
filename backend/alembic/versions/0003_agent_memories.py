"""Add agent_memories table

Revision ID: 0003_agent_memories
Revises: 0002_api_keys
Create Date: 2026-06-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0003_agent_memories"
down_revision: Union[str, None] = "0002_api_keys"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_memories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "workflow_id",
            sa.String(36),
            sa.ForeignKey("workflows.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("agent_node_id", sa.String(100), nullable=True),
        sa.Column("memory_type", sa.String(20), nullable=False, server_default="context"),
        sa.Column("key", sa.String(255), nullable=False, index=True),
        sa.Column("content", JSONB(), nullable=False, server_default="{}"),
        sa.Column("importance", sa.Float(), default=0.5),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("agent_memories")
