"""Add line-level review fields to expense lines.

Revision ID: 20260310_01
Revises: 20260205_01
Create Date: 2026-03-10
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260310_01"
down_revision = "20260205_01"
branch_labels = None
depends_on = None

REVIEW_STATUS_ENUM = sa.Enum(
    "Pending",
    "Approved",
    "Rejected",
    name="expense_line_review_status",
)


def upgrade() -> None:
    """Add review status and comment columns to expense line items."""

    connection = op.get_bind()
    REVIEW_STATUS_ENUM.create(connection, checkfirst=True)
    op.add_column(
        "expense_lines",
        sa.Column(
            "review_status",
            REVIEW_STATUS_ENUM,
            nullable=False,
            server_default="Pending",
        ),
    )
    op.add_column(
        "expense_lines",
        sa.Column("review_comment", sa.Text(), nullable=True),
    )
    op.alter_column("expense_lines", "review_status", server_default=None)


def downgrade() -> None:
    """Remove review columns from expense line items."""

    connection = op.get_bind()
    op.drop_column("expense_lines", "review_comment")
    op.drop_column("expense_lines", "review_status")
    REVIEW_STATUS_ENUM.drop(connection, checkfirst=True)
