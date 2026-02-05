"""Regression tests ensuring help content reflects expense-reporting workflows."""

from pathlib import Path


HELP_BLUEPRINT_PATH = Path("app/help.py")
HELP_INDEX_TEMPLATE_PATH = Path("templates/help/index.html")


def test_help_blueprint_removes_quote_specific_topics_and_routes() -> None:
    """Ensure quote-centric help topics/routes stay retired.

    Inputs:
        None. Reads source text from :data:`HELP_BLUEPRINT_PATH`.

    Outputs:
        None. Fails if deprecated quote help topics or routes are present.

    External dependencies:
        Uses :class:`pathlib.Path` to read repository files.
    """

    source = HELP_BLUEPRINT_PATH.read_text(encoding="utf-8")

    assert 'slug": "quoting"' not in source
    assert 'slug": "booking"' not in source
    assert '@help_bp.get("/quote-types")' not in source
    assert "def quote_types()" not in source
    assert '@help_bp.get("/booking")' not in source


def test_help_center_home_uses_expense_reporting_language() -> None:
    """Verify the help home template describes expense-reporting workflows.

    Inputs:
        None. Reads source text from :data:`HELP_INDEX_TEMPLATE_PATH`.

    Outputs:
        None. Asserts the overview references expense reporting topics and the
        expense workflow guide entry point.

    External dependencies:
        Uses :class:`pathlib.Path` to read repository files.
    """

    source = HELP_INDEX_TEMPLATE_PATH.read_text(encoding="utf-8")

    assert "Expense Reporting Help Center" in source
    assert "supervisor review" in source
    assert "help.expense_workflow" in source
