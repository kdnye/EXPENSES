"""Tests for line-by-line expense report review decisions."""

from types import SimpleNamespace
from pathlib import Path

from app.services.expense_workflow import (
    ExpenseLineDecision,
    apply_line_review_decisions,
)


def test_apply_line_review_decisions_approves_all_lines() -> None:
    """Approve a report when every line is marked approved.

    Inputs:
        None. Builds in-memory line objects to exercise the helper.

    Outputs:
        None. Asserts report and line statuses update correctly.

    External dependencies:
        Calls :func:`app.services.expense_workflow.apply_line_review_decisions`.
    """

    line_one = SimpleNamespace(id=1, status="Pending Review", rejection_comment=None)
    line_two = SimpleNamespace(id=2, status="Pending Review", rejection_comment=None)
    report = SimpleNamespace(
        lines=[line_one, line_two],
        status="Pending Review",
        rejection_comment="",
    )

    decisions = (
        ExpenseLineDecision(line_id=1, status="approve", comment=""),
        ExpenseLineDecision(line_id=2, status="approve", comment=""),
    )

    message, category = apply_line_review_decisions(report, decisions=decisions)

    assert report.status == "Pending Upload"
    assert report.rejection_comment is None
    assert line_one.status == "Approved"
    assert line_two.status == "Approved"
    assert message
    assert category == "success"


def test_apply_line_review_decisions_requires_rejection_comment() -> None:
    """Rejecting a line requires a comment for traceability.

    Inputs:
        None. Builds in-memory line objects to exercise the helper.

    Outputs:
        None. Asserts the helper raises for missing rejection comments.

    External dependencies:
        Calls :func:`app.services.expense_workflow.apply_line_review_decisions`.
    """

    line_one = SimpleNamespace(id=10, status="Pending Review", rejection_comment=None)
    report = SimpleNamespace(
        lines=[line_one],
        status="Pending Review",
        rejection_comment="",
    )

    decisions = (ExpenseLineDecision(line_id=10, status="reject", comment=""),)

    try:
        apply_line_review_decisions(report, decisions=decisions)
    except ValueError as exc:
        assert "comment" in str(exc).lower()
    else:
        raise AssertionError("Expected ValueError for missing rejection comment")


def test_review_report_template_includes_line_decisions() -> None:
    """Ensure the review template exposes line decision controls.

    Inputs:
        None. Reads the report review template from disk.

    Outputs:
        None. Asserts the template includes line decision fields.

    External dependencies:
        Uses :class:`pathlib.Path` to read repository files.
    """

    template = Path("templates/expenses/review_report.html").read_text(encoding="utf-8")

    assert "line_status_" in template
    assert "line_comment_" in template
    assert "Finalize Report" in template
