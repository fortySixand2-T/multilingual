"""truncate oversized display_name values

Revision ID: 0010_truncate_display_names
Revises: 0009_comprehension_pass
Create Date: 2026-06-21

Issue 130 capped display_name at 80 chars on signup, but pre-fix rows were not
cleaned. SQLite does not enforce String(120), so oversized values persist and
bloat the board response (qa-231).
"""

from __future__ import annotations

from alembic import op

revision = "0010_truncate_display_names"
down_revision = "0009_comprehension_pass"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE users SET display_name = substr(display_name, 1, 80)"
        " WHERE length(display_name) > 80"
    )


def downgrade() -> None:
    # Data-only migration; truncation is not reversible.
    pass
