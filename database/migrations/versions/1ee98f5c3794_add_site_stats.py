"""add_site_stats

Revision ID: 1ee98f5c3794
Revises: 2af8d64b9b12
Create Date: 2026-02-21 18:33:03.287850
"""

from alembic import op
import sqlalchemy as sa


revision: str = "1ee98f5c3794"
down_revision = "2af8d64b9b12"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "site_stats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("site_tag", sa.String(length=32), nullable=False),
        sa.Column("content_count", sa.Integer(), nullable=False),
        sa.Column("user_count", sa.Integer(), nullable=False),
        sa.Column("assets_mb", sa.Float(), nullable=False),
        sa.Column(
            "collected_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["site_tag"], ["sites.tag"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_site_stats_tag_collected",
        "site_stats",
        ["site_tag", "collected_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_site_stats_tag_collected", table_name="site_stats")
    op.drop_table("site_stats")
