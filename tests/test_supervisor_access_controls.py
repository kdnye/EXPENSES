"""Tests for supervisor access controls and picker eligibility."""

from pathlib import Path


def test_supervisor_routes_require_supervisor_role() -> None:
    """Ensure supervisor-only routes use the supervisor role guard.

    Inputs:
        None. Reads ``app/expenses.py`` to verify decorator usage.

    Outputs:
        None. Asserts the supervisor-only decorator is applied to routes.

    External dependencies:
        Uses :class:`pathlib.Path` to read source text from the repository.
    """

    source = Path("app/expenses.py").read_text(encoding="utf-8")

    assert "@supervisor_required(approved_only=True)" in source
    assert '@expenses_bp.route("/supervisor")' in source
    assert '@expenses_bp.route("/supervisor/report/<int:report_id>", methods=["GET", "POST"])' in source


def test_supervisor_required_enforces_approval() -> None:
    """Ensure supervisor access checks require approval for supervisors.

    Inputs:
        None. Reads ``app/policies.py`` to verify approval checks.

    Outputs:
        None. Asserts supervisors are subject to ``employee_approved`` checks.

    External dependencies:
        Uses :class:`pathlib.Path` to read source text from the repository.
    """

    source = Path("app/policies.py").read_text(encoding="utf-8")

    assert "def supervisor_required" in source
    assert 'roles_required("supervisor", require_employee_approval=approved_only)' in source
    assert 'user_role in {"employee", "supervisor"}' in source


def test_supervisor_picker_filters_approved_supervisors() -> None:
    """Ensure the supervisor picker is limited to approved supervisors.

    Inputs:
        None. Reads ``app/expenses.py`` to verify the query filters.

    Outputs:
        None. Asserts the supervisor query includes role and approval checks.

    External dependencies:
        Uses :class:`pathlib.Path` to read source text from the repository.
    """

    source = Path("app/expenses.py").read_text(encoding="utf-8")

    assert 'User.role == "supervisor"' in source
    assert "User.employee_approved.is_(True)" in source
