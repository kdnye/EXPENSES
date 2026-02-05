"""Tests for quote-tool route removal in the app factory module."""

from pathlib import Path


def test_quote_tool_routes_are_not_defined_in_app_init() -> None:
    """Verify quote-tool routes are absent from ``app/__init__.py``.

    Inputs:
        None. Reads ``app/__init__.py`` from disk.

    Outputs:
        None. Asserts the removed route decorators are no longer present.

    External dependencies:
        Uses :class:`pathlib.Path` to read source text from the repository.
    """

    init_source = Path("app/__init__.py").read_text(encoding="utf-8")

    assert '@app.route("/map", methods=["POST"])' not in init_source
    assert '@app.route("/send", methods=["POST"])' not in init_source
