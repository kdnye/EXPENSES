"""Blueprint exposing expense-report JSON API endpoints."""

from __future__ import annotations

import secrets
from typing import Dict

from flask import Blueprint, current_app, jsonify, request
from flask.typing import ResponseReturnValue


api_bp = Blueprint("api", __name__)


def _extract_api_token(authorization_header: str | None) -> str | None:
    """Return the API token provided in an Authorization header.

    Args:
        authorization_header: Raw ``Authorization`` header value supplied by the client.

    Returns:
        The token string when present in the header, otherwise ``None``. The
        ``Bearer`` scheme is only accepted when a token follows it.
    """

    if not authorization_header:
        return None

    parts = authorization_header.strip().split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    if len(parts) == 1 and parts[0].lower() != "bearer":
        return parts[0]
    return None


def _authorize_api_request() -> ResponseReturnValue | None:
    """Validate the API authentication header for JSON API requests.

    Returns:
        ``None`` when the request is authorized. Otherwise returns a JSON
        response with the appropriate HTTP status code.

    External dependencies:
        * Reads :data:`flask.current_app.config` for ``API_AUTH_TOKEN``.
        * Reads :data:`flask.request.headers` for the ``Authorization`` header.
        * Calls :func:`secrets.compare_digest` for constant-time comparison.
    """

    expected_token = current_app.config.get("API_AUTH_TOKEN")
    if not expected_token:
        return jsonify({"error": "API authentication is not configured."}), 500

    authorization_header = request.headers.get("Authorization")
    if not authorization_header:
        return jsonify({"error": "Missing Authorization header."}), 401

    provided_token = _extract_api_token(authorization_header)
    if not provided_token:
        return jsonify({"error": "Invalid Authorization header."}), 401

    if not secrets.compare_digest(provided_token, expected_token):
        return jsonify({"error": "Invalid API token."}), 403

    return None


@api_bp.before_request
def _require_api_auth() -> ResponseReturnValue | None:
    """Enforce API authentication before processing JSON API requests.

    Returns:
        ``None`` when authorization succeeds, otherwise a JSON error response.

    External dependencies:
        Delegates to :func:`_authorize_api_request` for validation.
    """

    return _authorize_api_request()


def _quote_endpoint_removed_response() -> tuple[Dict[str, str], int]:
    """Return a migration response for retired quote API routes.

    Returns:
        A JSON-safe payload and HTTP status code for legacy quote clients.

    External dependencies:
        None. This helper only returns a static payload.
    """

    payload = {
        "error": "Quote API has been removed.",
        "message": (
            "This service now supports expense-report workflows only. "
            "Migrate integrations away from /api/quote endpoints."
        ),
        "migration_path": "/expenses",
    }
    return payload, 410


@api_bp.post("/quote")
def api_create_quote() -> ResponseReturnValue:
    """Return a gone response for the retired quote creation endpoint.

    Returns:
        ``410 Gone`` response with migration guidance for legacy clients.

    External dependencies:
        Calls :func:`_quote_endpoint_removed_response` to build the payload.
    """

    payload, status_code = _quote_endpoint_removed_response()
    return jsonify(payload), status_code


@api_bp.get("/quote/<quote_id>")
def api_get_quote(quote_id: str) -> ResponseReturnValue:
    """Return a gone response for the retired quote retrieval endpoint.

    Args:
        quote_id: Quote identifier from the request path. Kept only for URL
            compatibility with older clients.

    Returns:
        ``410 Gone`` response with migration guidance for legacy clients.

    External dependencies:
        Calls :func:`_quote_endpoint_removed_response` to build the payload.
    """

    del quote_id
    payload, status_code = _quote_endpoint_removed_response()
    return jsonify(payload), status_code
