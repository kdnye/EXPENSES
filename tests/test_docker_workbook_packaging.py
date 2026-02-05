"""Checks for Docker packaging of the expense workbook template."""

from pathlib import Path


def test_dockerignore_allows_runtime_expense_template() -> None:
    """Ensure Docker ignore rules include the runtime workbook exception.

    Inputs:
        None.

    Outputs:
        None. Asserts ``.dockerignore`` keeps broad ``*.xlsx`` ignores while
        explicitly including ``expense_report_template.xlsx``.

    External dependencies:
        Reads repository files through :class:`pathlib.Path`.
    """

    dockerignore_content = Path(".dockerignore").read_text(encoding="utf-8")

    assert "*.xlsx" in dockerignore_content
    assert "!expense_report_template.xlsx" in dockerignore_content


def test_dockerfile_copies_build_context_into_app_directory() -> None:
    """Ensure Docker build context is copied so the workbook lands at ``/app``.

    Inputs:
        None.

    Outputs:
        None. Asserts the Dockerfile sets ``WORKDIR /app`` and executes
        ``COPY . .`` so repository files (including the workbook template) are
        available at runtime.

    External dependencies:
        Reads ``Dockerfile`` through :class:`pathlib.Path`.
    """

    dockerfile_content = Path("Dockerfile").read_text(encoding="utf-8")

    assert "WORKDIR /app" in dockerfile_content
    assert "COPY . ." in dockerfile_content
