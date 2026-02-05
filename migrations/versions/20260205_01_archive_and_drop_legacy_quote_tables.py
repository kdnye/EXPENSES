"""Archive and drop legacy quote-related tables.

Revision ID: 20260205_01
Revises:
Create Date: 2026-02-05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260205_01"
down_revision = None
branch_labels = None
depends_on = None

LEGACY_TABLES = (
    "quotes",
    "accessorials",
    "hotshot_rates",
    "beyond_rates",
    "air_cost_zones",
    "zip_zones",
    "rate_uploads",
)


def _table_exists(connection: sa.engine.Connection, table_name: str) -> bool:
    """Return ``True`` when ``table_name`` exists in the connected database.

    Args:
        connection: Active Alembic SQLAlchemy connection.
        table_name: Candidate table name to inspect.

    Returns:
        bool: ``True`` if the table exists, else ``False``.

    External dependencies:
        Calls :meth:`sqlalchemy.engine.reflection.Inspector.has_table` through
        :func:`sqlalchemy.inspect`.
    """

    inspector = sa.inspect(connection)
    return inspector.has_table(table_name)


def upgrade() -> None:
    """Archive legacy quote tables before dropping them.

    For each legacy table, this migration creates a same-schema backup table
    named ``archive_<table>_<revision>`` and copies all rows into it before
    dropping the original table.
    """

    connection = op.get_bind()

    for table_name in LEGACY_TABLES:
        if not _table_exists(connection, table_name):
            continue

        archive_table = f"archive_{table_name}_{revision}"
        if _table_exists(connection, archive_table):
            op.drop_table(archive_table)

        op.execute(
            sa.text(
                f"CREATE TABLE {archive_table} AS TABLE {table_name} WITH DATA"  # nosec B608
            )
        )
        op.drop_table(table_name)


def downgrade() -> None:
    """Recreate dropped legacy tables from archived copies when available."""

    connection = op.get_bind()

    for table_name in LEGACY_TABLES:
        archive_table = f"archive_{table_name}_{revision}"
        if not _table_exists(connection, archive_table):
            continue
        if _table_exists(connection, table_name):
            op.drop_table(table_name)
        op.execute(
            sa.text(
                f"CREATE TABLE {table_name} AS TABLE {archive_table} WITH DATA"  # nosec B608
            )
        )
