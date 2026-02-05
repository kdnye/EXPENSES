"""Regression tests for Expense Reporting branding text in shared templates."""

from pathlib import Path


def test_base_template_uses_expense_reporting_branding() -> None:
    """Ensure the shared base layout shows the updated application name.

    Inputs:
        None. Reads ``templates/base.html`` from disk.

    Outputs:
        None. Asserts legacy "Quote Tool" branding is removed from the
        default page title and navbar brand label.

    External dependencies:
        Uses :class:`pathlib.Path` to read template source content.
    """

    base_template_source = Path("templates/base.html").read_text(encoding="utf-8")

    assert "FSI Expense Reporting" in base_template_source
    assert "Quote Tool" not in base_template_source
