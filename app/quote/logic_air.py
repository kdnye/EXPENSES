"""Deprecated air-quote logic kept for backward-compatible imports.

The quote subsystem has been retired from active product workflows. This module
now provides a stable ``calculate_air_quote`` function signature that returns a
consistent error payload instead of querying legacy rate tables.
"""

from __future__ import annotations

from typing import Any, Dict


def calculate_air_quote(
    origin: str,
    destination: str,
    weight: float,
    accessorial_total: float,
    *args: Any,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Return a deprecation payload for legacy callers.

    Args:
        origin: Original origin ZIP code argument from quote callers.
        destination: Original destination ZIP code argument from quote callers.
        weight: Requested shipment weight in pounds.
        accessorial_total: Additional charges provided by the caller.
        *args: Unused positional compatibility arguments.
        **kwargs: Unused keyword compatibility arguments.

    Returns:
        Dict[str, Any]: A structured payload with ``error`` populated so
        callers can gracefully render migration guidance without raising.

    External dependencies:
        None. The legacy database-backed quote tables were removed, so this
        function intentionally performs no database I/O.
    """

    return {
        "zone": None,
        "quote_total": 0,
        "min_charge": None,
        "per_lb": None,
        "weight_break": None,
        "origin_beyond": None,
        "dest_beyond": None,
        "origin_charge": 0,
        "dest_charge": 0,
        "beyond_total": 0,
        "error": (
            "Air quote logic has been retired. Use the expense reporting "
            "workflow instead."
        ),
        "origin": origin,
        "destination": destination,
        "weight": weight,
        "accessorial_total": accessorial_total,
    }
