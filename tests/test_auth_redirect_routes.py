from pathlib import Path


def test_auth_login_and_oidc_success_redirect_to_expenses_reports() -> None:
    """Ensure authentication success flows land on the expenses report list.

    Inputs:
        None. The test reads ``app/auth.py`` from disk.

    Outputs:
        Asserts route handlers use ``url_for('expenses.my_reports')`` after
        standard and OIDC login succeed.

    External dependencies:
        Uses :class:`pathlib.Path` to read the source file.
    """

    auth_source = Path("app/auth.py").read_text(encoding="utf-8")

    assert 'return redirect(url_for("expenses.my_reports"))' in auth_source
    assert "Redirects to ``expenses.my_reports`` on success." in auth_source


def test_repository_contains_no_quote_new_quote_references() -> None:
    """Ensure quote-entry endpoint references are fully removed.

    Inputs:
        None. The test inspects selected source and template files that
        previously referenced ``quotes.new_quote``.

    Outputs:
        Asserts the deprecated endpoint string no longer appears.

    External dependencies:
        Uses :class:`pathlib.Path` file reads.
    """

    files_to_check = [
        Path("app/auth.py"),
        Path("app/quotes/routes.py"),
        Path("templates/help/expense_workflow.html"),
        Path("templates/quote_result.html"),
    ]

    existing_files = [path for path in files_to_check if path.exists()]

    for file_path in existing_files:
        content = file_path.read_text(encoding="utf-8")
        assert "quotes.new_quote" not in content
