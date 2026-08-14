"""Aliases whose ``Annotated`` values carry validator/serializer metadata.

This is the shape of Safir's ``IvoaIsoDatetime``. Sphinx renders an
alias's value — metadata included — into the alias's own page and into
every signature the alias annotates, then unparses the result into
cross-references, so each dataclass field of a
``BeforeValidator``/``PlainSerializer`` becomes a reference target of its
own.

The functions the metadata wraps live here rather than in the package that
re-exports the aliases, so the dotted ``func=`` fragment names a private
module path: that reference is the pre-existing private-path rung's
business, not the module-scoped fragment index's.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BeforeValidator, PlainSerializer

__all__ = ["IsoDatetime", "TrimmedName", "register"]


def normalize_isodatetime(value: str) -> datetime:
    """Parse an ISO 8601 timestamp."""
    return datetime.fromisoformat(value)


def isodatetime(value: datetime) -> str:
    """Render a timestamp as an ISO 8601 string."""
    return value.isoformat()


def strip_name(value: str) -> str:
    """Trim the whitespace around a name."""
    return value.strip()


type IsoDatetime = Annotated[
    datetime,
    BeforeValidator(normalize_isodatetime),
    PlainSerializer(isodatetime, return_type=str, when_used="json"),
]
"""A timestamp normalized on the way in and serialized as an ISO string.

``BeforeValidator``'s ``json_schema_input_type`` defaults to the
``PydanticUndefined`` sentinel, whose repr is a bare name no documentation
target can exist for, and ``PlainSerializer``'s ``when_used`` is a string
that Sphinx stringifies without its quotes into a bare ``json`` — the two
nitpick warnings of issue #385.
"""


TrimmedName = Annotated[
    str,
    BeforeValidator(strip_name),
    PlainSerializer(strip_name, return_type=str, when_used="always"),
]
"""A name trimmed on the way in, in assignment-alias form.

``when_used`` differs from ``IsoDatetime``'s so that ``always`` is a
fragment only *this* alias renders.
"""


def register(name: TrimmedName) -> None:
    """Register a name, taking the assignment-style alias as a parameter.

    An assignment alias knows neither its own name nor its module, so
    Sphinx renders this parameter's annotation as the alias's whole
    ``Annotated`` value — metadata and all — on a page whose references
    carry a ``py:module`` context and no ``py:class`` at all.
    """
