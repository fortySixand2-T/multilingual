"""init: users table

Revision ID: 0001_init
Revises:
Create Date: 2026-06-15

Initial schema for Phase 0. Creates the `users` table (invite-code signup +
JWT auth). Hand-authored so the up/down cycle is reproducible without a live
autogenerate run; future schema changes should use
`alembic revision --autogenerate`.
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        # Inline so the unique index is created with the table — SQLite has no
        # ALTER-ADD-CONSTRAINT, so a post-hoc op.create_unique_constraint fails.
        sa.UniqueConstraint("email", name="uq_users_email"),
    )


def downgrade() -> None:
    op.drop_table("users")
