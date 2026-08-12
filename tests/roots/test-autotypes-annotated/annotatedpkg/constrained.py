"""Models whose annotations Sphinx renders from the runtime objects.

This module deliberately does *not* use ``from __future__ import
annotations``, so its annotations are real ``Annotated`` objects and
Sphinx renders each field's type by stringifying them — which writes the
``repr()`` of the field's metadata into the rendered type.
"""

from typing import Annotated

from pydantic import BaseModel, Field, FilePath

__all__ = ["KafkaSettings", "SentryConfig"]


class SentryConfig(BaseModel):
    """Settings whose field metadata carries value constraints.

    This is the shape of Safir's ``SentryConfig.traces_sample_rate``.
    """

    traces_sample_rate: Annotated[
        float, Field(ge=0, le=1, description="Fraction of traces to send.")
    ] = 0.0
    """A field whose ``FieldInfo`` repr nests ``annotated_types`` objects.

    Pydantic turns ``ge``/``le`` into ``Ge`` and ``Le`` instances in the
    field's metadata, so the rendered type reads ``Annotated[float,
    FieldInfo(annotation=NoneType, ..., metadata=[Ge(ge=0), Le(le=1)])]``.
    That parses as Python, so the annotation parser splits it into parts
    and emits bare ``Ge`` and ``Le`` cross-references. ``annotated_types``
    is in none of this model's MRO package roots, so no resolution rung
    reaches them.
    """


class KafkaSettings(BaseModel):
    """Settings with a path-type constraint on a field.

    This is the shape of Safir's ``KafkaConnectionSettings`` TLS paths.
    """

    cluster_ca_path: Annotated[
        FilePath | None, Field(description="Path to the cluster CA.")
    ] = None
    """A field whose metadata is a dataclass with a string field value.

    Pydantic's ``FilePath`` expands to ``Annotated[Path,
    PathType('file')]``, and ``PathType`` is a dataclass — which Sphinx
    renders by stringifying each field value rather than by ``repr()``,
    dropping the quotes from ``'file'``. The rendered
    ``PathType(path_type=file)`` then unparses into a bare ``file``
    cross-reference: a value fragment that never named an object at all.
    """
