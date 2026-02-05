from pathlib import Path


def test_expense_form_uses_dynamic_gl_account_select() -> None:
    """Ensure the expense form uses a dynamic select fed by the GL endpoint."""

    template_path = Path("templates/expenses/new_expense.html")
    content = template_path.read_text(encoding="utf-8")

    assert (
        "const glAccountsEndpoint = \"{{ url_for('expenses.gl_accounts_options') }}\";"
        in content
    )
    assert '<select class="form-select" name="gl_account" required>' in content
    assert '<datalist id="gl-account-options">' not in content


def test_expenses_module_exposes_gl_accounts_endpoint() -> None:
    """Ensure expenses routes include the JSON endpoint used by frontend validation."""

    module_path = Path("expenses.py")
    content = module_path.read_text(encoding="utf-8")

    assert '@expenses_bp.get("/gl-accounts")' in content
    assert "select a GL account from the approved list" in content
