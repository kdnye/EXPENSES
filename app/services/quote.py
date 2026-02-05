"""Deprecated quote service layer.

Legacy quote persistence models have been removed from ``app.models``.
Functions in this module remain import-compatible for older callers but now
return safe deprecation responses instead of reading or writing retired tables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.quote.logic_air import calculate_air_quote


@dataclass
class DeprecatedQuote:
    """Minimal quote-like object returned to legacy callers.

    Args:
        quote_id: Placeholder identifier used by old view templates.
        created_at: Timestamp included for compatibility with sort/display code.
        warnings: Human-readable migration guidance message.

    Returns:
        None. This is a data container used by legacy function outputs.

    External dependencies:
        None. This class stores values in memory only.
    """

    quote_id: str = "quote-retired"
    created_at: datetime = field(default_factory=datetime.utcnow)
    warnings: str = "Quote storage has been retired from this application."


def get_accessorial_options(quote_type: str) -> List[str]:
    """Return an empty accessorial list for retired quote workflows.

    Args:
        quote_type: Historical quote type name from legacy forms.

    Returns:
        List[str]: Always an empty list because accessorial tables were removed.

    External dependencies:
        None.
    """

    return []


def create_quote(*args: Any, **kwargs: Any) -> Tuple[DeprecatedQuote, Dict[str, Any]]:
    """Return a placeholder quote and deprecation metadata.

    Args:
        *args: Legacy positional arguments.
        **kwargs: Legacy keyword arguments. Supports ``origin``,
            ``destination``, ``weight``, and ``accessorial_total`` when present.

    Returns:
        Tuple[DeprecatedQuote, Dict[str, Any]]: Placeholder quote-like object and
        metadata containing a deprecation error payload.

    External dependencies:
        Calls :func:`app.quote.logic_air.calculate_air_quote` to produce a
        consistent deprecation payload shape for UI compatibility.
    """

    metadata = calculate_air_quote(
        origin=str(kwargs.get("origin", "")),
        destination=str(kwargs.get("destination", "")),
        weight=float(kwargs.get("weight", 0) or 0),
        accessorial_total=float(kwargs.get("accessorial_total", 0) or 0),
    )
    return DeprecatedQuote(), metadata


def get_quote(quote_id: str) -> Optional[DeprecatedQuote]:
    """Return ``None`` for retired quote records.

    Args:
        quote_id: Legacy quote identifier.

    Returns:
        Optional[DeprecatedQuote]: Always ``None`` because quote rows are no
        longer persisted.

    External dependencies:
        None.
    """

    return None


def list_quotes() -> List[DeprecatedQuote]:
    """Return an empty list because quote storage is retired.

    Args:
        None.

    Returns:
        List[DeprecatedQuote]: Always an empty list.

    External dependencies:
        None.
    """

    return []


def create_email_request(*args: Any, **kwargs: Any) -> None:
    """No-op legacy shim for removed quote email request persistence.

    Args:
        *args: Legacy positional arguments.
        **kwargs: Legacy keyword arguments.

    Returns:
        None.

    External dependencies:
        None.
    """

    return None
