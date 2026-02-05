"""Helpers used by admin CSV upload workflows.

This module currently exposes ``save_unique`` so ``app.admin.upload_csv`` can
append rows while skipping duplicates based on a model attribute.
"""

from __future__ import annotations

from typing import Any, Iterable, Tuple, Type

from sqlalchemy.orm import Session


def save_unique(
    session: Session,
    model: Type[Any],
    objects: Iterable[Any],
    unique_attr: str,
) -> Tuple[int, int]:
    """Persist only rows whose unique key is not already present.

    Inputs:
        session: Active SQLAlchemy session used to query and persist records.
            The caller (``app.admin.upload_csv``) controls transaction commit.
        model: SQLAlchemy model class associated with ``objects``.
        objects: Candidate model instances to insert.
        unique_attr: Name of the model attribute used as a de-duplication key.

    Outputs:
        Tuple[int, int]: ``(inserted_count, skipped_count)`` describing how
        many rows were saved versus ignored as duplicates.

    External dependencies:
        Calls ``sqlalchemy.orm.Session.query`` against ``model`` to load
        existing key values and ``session.bulk_save_objects`` to insert only
        unseen rows.
    """

    existing_values = {
        value
        for (value,) in session.query(getattr(model, unique_attr)).all()
        if value is not None
    }

    unique_objects = []
    skipped = 0
    for obj in objects:
        value = getattr(obj, unique_attr, None)
        if value in existing_values:
            skipped += 1
            continue
        existing_values.add(value)
        unique_objects.append(obj)

    if unique_objects:
        session.bulk_save_objects(unique_objects)

    return len(unique_objects), skipped
