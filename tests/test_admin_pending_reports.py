"""Tests covering admin pending review dashboard additions."""

from pathlib import Path


def test_admin_dashboard_includes_pending_report_section() -> None:
    """Ensure the admin dashboard template includes pending report markup.

    Inputs:
        None. Reads the admin dashboard template from the repository.

    Outputs:
        None. Asserts the pending report section and review link exist.

    External dependencies:
        Uses :class:`pathlib.Path` to read template text from disk.
    """

    template = Path("templates/admin_dashboard.html").read_text(encoding="utf-8")

    assert "Pending Report Reviews" in template
    assert "pending_reports" in template
    assert "admin.review_report" in template


def test_admin_review_route_requires_super_admin() -> None:
    """Ensure the admin review route uses super admin access control.

    Inputs:
        None. Reads the admin blueprint source file.

    Outputs:
        None. Asserts the review route is protected by ``super_admin_required``.

    External dependencies:
        Uses :class:`pathlib.Path` to read source text from the repository.
    """

    source = Path("app/admin.py").read_text(encoding="utf-8")

    assert '@admin_bp.route("/reports/<int:report_id>/review"' in source
    assert "@super_admin_required" in source


def test_admin_dashboard_loads_pending_reports() -> None:
    """Ensure the admin dashboard queries pending reports.

    Inputs:
        None. Reads the admin blueprint source file.

    Outputs:
        None. Asserts the pending review query helper is invoked.

    External dependencies:
        Uses :class:`pathlib.Path` to read source text from the repository.
    """

    source = Path("app/admin.py").read_text(encoding="utf-8")

    assert "pending_reports = _pending_review_reports()" in source
