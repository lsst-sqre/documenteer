"""A second module of the same package, with an ``Annotated`` alias of its own.

Its alias carries a serializer but no validator, so its metadata renders
neither the ``PydanticUndefined`` sentinel nor the ``always`` string value
that the package's own aliases do. That is what makes the fragment
index's per-module scope observable: a fragment of one module's alias must
not degrade under another module's ``py:module`` context.

Nothing documents this module, so no reference is ever emitted for its own
contents; it exists to be the second module the index is asked about.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import PlainSerializer

__all__ = ["LegacyDatetime"]


def legacy_isodatetime(value: datetime) -> str:
    """Render a timestamp the way the legacy API did."""
    return value.isoformat(sep=" ")


type LegacyDatetime = Annotated[
    datetime,
    PlainSerializer(legacy_isodatetime, return_type=str, when_used="json"),
]
"""A timestamp serialized as a string in the legacy format."""
