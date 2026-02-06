"""Add line-level review status and comments to expense lines.

Revision ID: 20260215_01
Revises: 20260205_01
Create Date: 2026-02-15
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260215_01"
down_revision = "20260205_01"
branch_labels = None
depends_on = None


LINE_STATUS_ENUM = sa.Enum(
    "Pending Review",
    "Approved",
    "Rejected",
    name="expense_line_status",
)


def upgrade() -> None:
    """Add status and rejection comment columns for expense lines."""

    connection = op.get_bind()
    LINE_STATUS_ENUM.create(connection, checkfirst=True)

    op.add_column(
        "expense_lines",
        sa.Column(
            "status",
            LINE_STATUS_ENUM,
            nullable=False,
            server_default="Pending Review",
        ),
    )
    op.add_column(
        "expense_lines",
        sa.Column("rejection_comment", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Remove line-level status and comment fields from expense lines."""

    op.drop_column("expense_lines", "rejection_comment")
    op.drop_column("expense_lines", "status")
    connection = op.get_bind()
    LINE_STATUS_ENUM.drop(connection, checkfirst=True)
