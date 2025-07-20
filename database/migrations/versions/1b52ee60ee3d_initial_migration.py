"""initial_migration

Revision ID: 1b52ee60ee3d
Revises:
Create Date: 2025-07-20 12:54:52.560792
"""

import sqlalchemy as sa
from alembic import op

revision: str = "1b52ee60ee3d"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sites",
        sa.Column("id", sa.String(length=4), nullable=False),
        sa.Column("admin_email", sa.String(length=255), nullable=False),
        sa.Column("admin_password", sa.String(length=72), nullable=False),
        sa.Column("site_type", sa.String(length=30), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column("chroot_dir", sa.String(length=255), nullable=False),
        sa.Column("installed_at", sa.DateTime(), nullable=True),
        sa.Column("removal_reason", sa.String(length=255), nullable=True),
        sa.Column("removed_at", sa.DateTime(), nullable=True),
        sa.Column("removed_ip", sa.String(length=45), nullable=True),
        sa.Column("created_ip", sa.String(length=45), nullable=True),
        sa.Column("last_login_ip", sa.String(length=45), nullable=True),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("donated_amount", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("sites")
