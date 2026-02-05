"""Gunicorn entrypoint exposing the Flask application factory."""

from __future__ import annotations

try:
    from . import create_app
except ImportError:  # pragma: no cover - direct script/module fallback
    from __init__ import create_app

__all__ = ["create_app"]
