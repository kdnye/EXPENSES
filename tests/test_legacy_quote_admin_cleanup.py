"""Regression tests for legacy quote schema/admin cleanup."""

from pathlib import Path


MODELS_PATH = Path("app/models.py")
ADMIN_PATH = Path("app/admin.py")
DASHBOARD_TEMPLATE_PATH = Path("templates/admin_dashboard.html")
MIGRATION_PATH = Path(
    "migrations/versions/20260205_01_archive_and_drop_legacy_quote_tables.py"
)


def test_models_remove_legacy_quote_model_classes() -> None:
    """Assert quote-related ORM classes were removed from ``app/models.py``.

    Inputs:
        None. Reads source code from :data:`MODELS_PATH`.

    Outputs:
        None. Fails if removed class declarations reappear.

    External dependencies:
        Uses :class:`pathlib.Path` to read repository files.
    """

    source = MODELS_PATH.read_text(encoding="utf-8")

    assert "class Quote(" not in source
    assert "class Accessorial(" not in source
    assert "class HotshotRate(" not in source
    assert "class BeyondRate(" not in source
    assert "class AirCostZone(" not in source
    assert "class ZipZone(" not in source
    assert "class RateUpload(" not in source


def test_admin_removes_legacy_quote_routes_and_forms() -> None:
    """Assert legacy quote admin forms/routes are absent from ``app/admin.py``.

    Inputs:
        None. Reads source code from :data:`ADMIN_PATH`.

    Outputs:
        None. Fails if legacy quote admin endpoints or forms are restored.

    External dependencies:
        Uses :class:`pathlib.Path` to read repository files.
    """

    source = ADMIN_PATH.read_text(encoding="utf-8")

    assert "class AccessorialForm(" not in source
    assert "class BeyondRateForm(" not in source
    assert "class HotshotRateForm(" not in source
    assert "class ZipZoneForm(" not in source
    assert "class AirCostZoneForm(" not in source

    assert '@admin_bp.route("/accessorials")' not in source
    assert '@admin_bp.route("/beyond_rates")' not in source
    assert '@admin_bp.route("/hotshot_rates")' not in source
    assert '@admin_bp.route("/zip_zones")' not in source
    assert '@admin_bp.route("/air_cost_zones")' not in source


def test_admin_dashboard_removes_legacy_quote_menu_links() -> None:
    """Assert the admin dashboard no longer links to removed quote tools.

    Inputs:
        None. Reads source code from :data:`DASHBOARD_TEMPLATE_PATH`.

    Outputs:
        None. Fails if removed menu links are reintroduced.

    External dependencies:
        Uses :class:`pathlib.Path` to read repository files.
    """

    source = DASHBOARD_TEMPLATE_PATH.read_text(encoding="utf-8")

    assert "admin.list_accessorials" not in source
    assert "admin.list_beyond_rates" not in source
    assert "admin.list_hotshot_rates" not in source
    assert "admin.list_zip_zones" not in source
    assert "admin.list_air_cost_zones" not in source


def test_migration_archives_before_drop() -> None:
    """Ensure migration script includes archive-before-drop workflow.

    Inputs:
        None. Reads source code from :data:`MIGRATION_PATH`.

    Outputs:
        None. Fails when backup/archive steps are missing.

    External dependencies:
        Uses :class:`pathlib.Path` to read repository files.
    """

    source = MIGRATION_PATH.read_text(encoding="utf-8")

    assert "archive_" in source
    assert "CREATE TABLE" in source
    assert "op.drop_table" in source
