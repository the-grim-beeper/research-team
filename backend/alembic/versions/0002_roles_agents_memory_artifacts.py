"""roles, agents, artifacts, memory tables; seed default roles

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-10
"""
from collections.abc import Sequence
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

from app.initial_roles import role_seed_rows

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("category", sa.String(16), nullable=False),
        sa.Column("default_system_prompt", sa.Text(), nullable=False),
        sa.Column("default_model", sa.String(128), nullable=False),
        sa.Column("default_cycle", sa.String(16), nullable=False),
        sa.Column("default_tier", sa.String(16), nullable=False),
        sa.Column("tools", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("slug", name="uq_roles_slug"),
    )

    op.create_table(
        "agents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "subject_id",
            sa.Integer(),
            sa.ForeignKey("subjects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("cycle", sa.String(16), nullable=False),
        sa.Column("daily_budget_usd", sa.Numeric(10, 4), nullable=False, server_default="1.0"),
        sa.Column("spent_today_usd", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agents_subject_id", "agents", ["subject_id"])

    op.create_table(
        "artifacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "subject_id",
            sa.Integer(),
            sa.ForeignKey("subjects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("author_type", sa.String(8), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=True),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("artifacts.id"), nullable=True),
        sa.Column("addressed_to", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(255), nullable=False, server_default=""),
        sa.Column("body_md", sa.Text(), nullable=False, server_default=""),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_artifacts_subject_id", "artifacts", ["subject_id"])
    op.create_index("ix_artifacts_parent_id", "artifacts", ["parent_id"])

    op.create_table(
        "memory_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "agent_id",
            sa.Integer(),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("importance", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_memory_entries_agent_id", "memory_entries", ["agent_id"])

    op.create_table(
        "agent_memory_vectors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "agent_id",
            sa.Integer(),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column(
            "source_artifact_id",
            sa.Integer(),
            sa.ForeignKey("artifacts.id"),
            nullable=True,
        ),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_memory_vectors_agent_id", "agent_memory_vectors", ["agent_id"])
    op.execute(
        "CREATE INDEX ix_agent_memory_vectors_embedding "
        "ON agent_memory_vectors USING hnsw (embedding vector_cosine_ops)"
    )

    now = datetime.now(timezone.utc)
    rows = [{**r, "created_at": now} for r in role_seed_rows()]
    op.bulk_insert(
        sa.table(
            "roles",
            sa.column("slug", sa.String),
            sa.column("display_name", sa.String),
            sa.column("category", sa.String),
            sa.column("default_system_prompt", sa.Text),
            sa.column("default_model", sa.String),
            sa.column("default_cycle", sa.String),
            sa.column("default_tier", sa.String),
            sa.column("tools", sa.JSON),
            sa.column("created_at", sa.DateTime(timezone=True)),
        ),
        rows,
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_agent_memory_vectors_embedding")
    op.drop_index("ix_agent_memory_vectors_agent_id", table_name="agent_memory_vectors")
    op.drop_table("agent_memory_vectors")
    op.drop_index("ix_memory_entries_agent_id", table_name="memory_entries")
    op.drop_table("memory_entries")
    op.drop_index("ix_artifacts_parent_id", table_name="artifacts")
    op.drop_index("ix_artifacts_subject_id", table_name="artifacts")
    op.drop_table("artifacts")
    op.drop_index("ix_agents_subject_id", table_name="agents")
    op.drop_table("agents")
    op.drop_table("roles")
