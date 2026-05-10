"""sources, corpus_items, bibliography_entries

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-10
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "subject_id",
            sa.Integer(),
            sa.ForeignKey("subjects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sources_subject_id", "sources", ["subject_id"])

    op.create_table(
        "corpus_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "subject_id",
            sa.Integer(),
            sa.ForeignKey("subjects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("sources.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("external_id", sa.String(512), nullable=True),
        sa.Column("title", sa.String(512), nullable=False, server_default=""),
        sa.Column("authors_json", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("url", sa.String(1024), nullable=True),
        sa.Column("text", sa.Text(), nullable=False, server_default=""),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("tags_json", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("importance", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "subject_id", "source_id", "external_id", name="uq_corpus_external"
        ),
    )
    op.create_index("ix_corpus_items_subject_id", "corpus_items", ["subject_id"])
    op.create_index("ix_corpus_items_source_id", "corpus_items", ["source_id"])

    op.create_table(
        "bibliography_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "subject_id",
            sa.Integer(),
            sa.ForeignKey("subjects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "corpus_item_id",
            sa.Integer(),
            sa.ForeignKey("corpus_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("comments", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("corpus_item_id", name="uq_bibliography_corpus_item"),
    )
    op.create_index("ix_bibliography_entries_subject_id", "bibliography_entries", ["subject_id"])


def downgrade() -> None:
    op.drop_index("ix_bibliography_entries_subject_id", table_name="bibliography_entries")
    op.drop_table("bibliography_entries")
    op.drop_index("ix_corpus_items_source_id", table_name="corpus_items")
    op.drop_index("ix_corpus_items_subject_id", table_name="corpus_items")
    op.drop_table("corpus_items")
    op.drop_index("ix_sources_subject_id", table_name="sources")
    op.drop_table("sources")
