from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import pytest

from app.services.expense_workflow import apply_line_item_review_actions


@dataclass
class DummyLine:
    """Minimal expense line for unit testing review decisions.

    Inputs:
        id: Unique identifier for the line item under review.
        review_status: Current review state for the line item.
        review_comment: Optional reviewer notes tied to the line.

    Outputs:
        A lightweight container for line review attributes used in tests.

    External dependencies:
        None.
    """

    id: int
    review_status: str = "Pending"
    review_comment: Optional[str] = None


@dataclass
class DummyReport:
    """Minimal expense report wrapper for unit testing review decisions.

    Inputs:
        lines: Collection of :class:`DummyLine` entries attached to the report.
        status: Current report status value.
        rejection_comment: Optional report-level rejection summary.

    Outputs:
        A lightweight container for report review attributes used in tests.

    External dependencies:
        None.
    """

    lines: List[DummyLine] = field(default_factory=list)
    status: str = "Pending Review"
    rejection_comment: Optional[str] = None


def test_apply_line_item_review_actions_approves_all_lines() -> None:
    """Ensure all approved lines move the report to pending upload.

    Inputs:
        None. Constructs a minimal in-memory report with two line items.

    Outputs:
        None. Asserts report and line state transitions in memory.

    External dependencies:
        Calls :func:`app.services.expense_workflow.apply_line_item_review_actions`.
    """

    report = DummyReport(lines=[DummyLine(id=1), DummyLine(id=2)])
    decisions = {1: ("approve", ""), 2: ("approve", "")}

    message, category = apply_line_item_review_actions(report, decisions=decisions)

    assert message.startswith("All expense lines approved")
    assert category == "success"
    assert report.status == "Pending Upload"
    assert report.rejection_comment is None
    assert [line.review_status for line in report.lines] == ["Approved", "Approved"]


def test_apply_line_item_review_actions_requires_rejection_comment() -> None:
    """Rejecting a line without notes should raise a helpful error.

    Inputs:
        None. Constructs a minimal in-memory report with one line item.

    Outputs:
        None. Asserts a :class:`ValueError` is raised for missing comments.

    External dependencies:
        Calls :func:`app.services.expense_workflow.apply_line_item_review_actions`.
    """

    report = DummyReport(lines=[DummyLine(id=1)])
    decisions = {1: ("reject", "")}

    with pytest.raises(ValueError, match="rejection comment"):
        apply_line_item_review_actions(report, decisions=decisions)


def test_apply_line_item_review_actions_marks_rejected_lines() -> None:
    """Rejected lines should return the report to draft with feedback.

    Inputs:
        None. Constructs a minimal in-memory report with two line items.

    Outputs:
        None. Asserts report and line state transitions in memory.

    External dependencies:
        Calls :func:`app.services.expense_workflow.apply_line_item_review_actions`.
    """

    report = DummyReport(lines=[DummyLine(id=1), DummyLine(id=2)])
    decisions = {1: ("approve", ""), 2: ("reject", "Missing receipt")}

    message, category = apply_line_item_review_actions(report, decisions=decisions)

    assert message.startswith("Report returned to draft")
    assert category == "info"
    assert report.status == "Draft"
    assert report.rejection_comment == "Line-level feedback provided."
    assert report.lines[0].review_status == "Approved"
    assert report.lines[1].review_status == "Rejected"
    assert report.lines[1].review_comment == "Missing receipt"
