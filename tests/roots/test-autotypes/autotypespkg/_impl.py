"""Private implementation module for the autotypes test package."""

from typing import Annotated, TypeVar

import pydantic
from pydantic import BaseModel, Field, HttpUrl

T = TypeVar("T")

type StampValue = int | str | None
"""A value that can be stamped into a registry."""


class Point:
    """A sample class referenced from an ``Annotated`` alias."""

    x: int
    y: int

    def shifted[U: "Point"](self: U, dx: int) -> U:
        """Return a copy shifted by ``dx``.

        Returns
        -------
        U
            The shifted point.
        """
        raise NotImplementedError


SerializablePoint = Annotated[Point, "serialization-marker"]
"""A `Point` annotated for serialization."""


class Registry:
    """A registry of stamped values.

    The `StampValue` alias and the `SerializablePoint` alias are used in
    annotations, and `T` appears in docstrings. The registry's home page
    is a `HttpUrl`, an external class from a package with no intersphinx
    inventory.

    Parameters
    ----------
    values
        Mapping of names to values (`StampValue`).
    """

    home_page: HttpUrl | None = None

    def __init__(self, values: dict[str, StampValue] | None = None) -> None:
        self._values = values or {}

    def get(self, name: str) -> StampValue:
        """Get a value by name.

        Returns
        -------
        StampValue
            The stored value.
        """
        return self._values[name]

    def origin(self) -> SerializablePoint:
        """Return the origin as a serializable point.

        Returns
        -------
        SerializablePoint
            The origin point.
        """
        raise NotImplementedError


class Stamper[P: Point]:
    """A generic class with a :pep:`695` scoped type parameter.

    sphinx-autodoc-typehints renders the scoped parameter ``P`` with a
    bogus ``typing.`` prefix, so it is referenced here the way that
    extension emits it: `typing.P`. The ``typing`` module has no such
    member, so the reference is really to the scoped parameter.
    """

    def stamp(self, item: P) -> P:
        """Stamp an item.

        Parameters
        ----------
        item
            The item to stamp, of type `typing.P`.

        Returns
        -------
        typing.P
            The stamped item.
        """
        raise NotImplementedError


class BaseSettingsModel(BaseModel):
    """An intermediate base model that redeclares ``model_config``.

    This mirrors the shared base models (such as Safir's
    ``CamelCaseModel``) that Rubin projects put between
    `pydantic.BaseModel` and their own models. ``model_config`` is set
    here without a docstring of its own, so a subclass that documents it
    inherits ``pydantic.BaseModel.model_config``'s docstring instead —
    and that docstring references a bare ``ConfigDict``, a name that only
    Pydantic's own modules import. ``ConfigDict`` is deliberately
    referenced through the ``pydantic`` module here so that it is not a
    member of this package's namespace either.
    """

    model_config = pydantic.ConfigDict(populate_by_name=True)


class StampSettings(BaseSettingsModel):
    """Settings for stamping, with ``Annotated`` field metadata.

    autodoc-pydantic renders the ``repr()`` of a field's ``Annotated``
    metadata into its type, so a lambda or an enum member leaks into
    cross-reference targets such as
    `FieldInfo(annotation=NoneType, required=False, default_factory=<lambda>)`,
    which can never name a Python object.
    """

    enabled: Annotated[
        bool,
        Field(default_factory=lambda: True, description="Whether stamping."),
    ]


def combine(a: StampValue, b: StampValue) -> StampValue:
    """Combine two stamp values.

    Parameters
    ----------
    a
        First value, of type `T`.
    b
        Second value.

    Returns
    -------
    StampValue
        The combined value.
    """
    raise NotImplementedError
