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

    module_path = Path("app/expenses.py")
    content = module_path.read_text(encoding="utf-8")

    assert '@expenses_bp.get("/gl-accounts")' in content
    assert "select a GL account from the approved list" in content


def test_new_expense_uses_renamed_reference_workbook() -> None:
    """Ensure the new expense route advertises the renamed workbook template."""

    module_path = Path("app/expenses.py")
    content = module_path.read_text(encoding="utf-8")

    assert 'reference_workbook="expense_report_template.xlsx"' in content
    assert "Dave Alexander Expense Report 12.12.2023.xlsx" not in content
