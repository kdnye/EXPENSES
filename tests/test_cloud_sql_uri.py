"""Tests for Cloud SQL URI assembly and scripts package imports."""

from scripts.import_air_rates import save_unique

from config import build_cloud_sql_unix_socket_uri_from_env


def test_cloud_sql_uri_uses_sqlalchemy_cloud_sql_socket_format(monkeypatch):
    """Build a Cloud SQL DSN that points to the unix socket path.

    Inputs:
        monkeypatch: pytest fixture used to set Cloud SQL env variables.

    Outputs:
        None. Asserts the generated DSN shape expected by SQLAlchemy's
        Cloud SQL socket configuration.

    External dependencies:
        Calls ``config.build_cloud_sql_unix_socket_uri_from_env``.
    """

    monkeypatch.setenv("CLOUD_SQL_CONNECTION_NAME", "project-1:us-central1:expenses-db")
    monkeypatch.setenv("POSTGRES_USER", "postgres")
    monkeypatch.setenv("POSTGRES_PASSWORD", "abc&123")
    monkeypatch.setenv("POSTGRES_DB", "postgres")

    uri = build_cloud_sql_unix_socket_uri_from_env()

    assert uri is not None
    assert uri.startswith("postgresql+")
    assert "abc%26123" in uri
    assert (
        "unix_sock=/cloudsql/project-1%3Aus-central1%3Aexpenses-db/.s.PGSQL.5432"
        in uri
    )


def test_scripts_package_is_importable_and_exposes_save_unique():
    """Confirm the scripts package resolves and exposes ``save_unique``.

    Inputs:
        None.

    Outputs:
        None. Asserts the imported symbol is callable.

    External dependencies:
        Imports ``scripts.import_air_rates.save_unique``.
    """

    assert callable(save_unique)
