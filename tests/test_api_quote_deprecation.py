"""Regression tests for deprecated quote API endpoints in ``app.api``."""

from __future__ import annotations

from flask import Flask
from flask.testing import FlaskClient

from app.api import api_bp


def _make_client(api_token: str = "test-token") -> FlaskClient:
    """Create a minimal Flask test client with the API blueprint registered.

    Args:
        api_token: Shared bearer token written to ``API_AUTH_TOKEN`` for
            :func:`app.api._authorize_api_request`.

    Returns:
        Flask test client bound to an in-memory application.

    External dependencies:
        Calls :func:`flask.Flask.register_blueprint` to mount :data:`app.api.api_bp`.
    """

    app = Flask(__name__)
    app.config["API_AUTH_TOKEN"] = api_token
    app.register_blueprint(api_bp, url_prefix="/api")
    return app.test_client()


def test_quote_create_endpoint_returns_410_with_migration_message() -> None:
    """Ensure legacy quote-create route provides explicit migration guidance.

    Inputs:
        None. Sends an authenticated ``POST`` request to ``/api/quote``.

    Outputs:
        Verifies ``410`` response status and migration fields in JSON payload.

    External dependencies:
        Exercises :func:`app.api.api_create_quote` through Flask routing.
    """

    client = _make_client()

    response = client.post("/api/quote", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 410
    assert response.json == {
        "error": "Quote API has been removed.",
        "message": (
            "This service now supports expense-report workflows only. "
            "Migrate integrations away from /api/quote endpoints."
        ),
        "migration_path": "/expenses",
    }


def test_quote_get_endpoint_returns_410_with_migration_message() -> None:
    """Ensure legacy quote-read route provides explicit migration guidance.

    Inputs:
        None. Sends an authenticated ``GET`` request to
        ``/api/quote/<quote_id>``.

    Outputs:
        Verifies ``410`` response status and migration fields in JSON payload.

    External dependencies:
        Exercises :func:`app.api.api_get_quote` through Flask routing.
    """

    client = _make_client()

    response = client.get(
        "/api/quote/legacy-quote-id", headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 410
    assert response.json == {
        "error": "Quote API has been removed.",
        "message": (
            "This service now supports expense-report workflows only. "
            "Migrate integrations away from /api/quote endpoints."
        ),
        "migration_path": "/expenses",
    }
