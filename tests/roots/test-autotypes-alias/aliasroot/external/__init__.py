"""A package the documented one uses but does not document.

This stands in for ``lsst.resources``: it publishes a plain-assignment
union type alias that the documented package writes into its own
annotations and docstrings, and no intersphinx inventory covers it.

The alias binds its name to a bare union object, which — unlike a
:pep:`695` ``type`` statement or a ``TypeVar`` — knows neither the name it
was assigned to nor the module it was written in, so only the module it is
*found* in identifies it as external.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["PathExpression", "read_path"]

PathExpression = str | Path
"""Anything that can be interpreted as a path."""


def read_path(path: PathExpression) -> bytes:
    """Read the bytes at *path*."""
    return Path(path).read_bytes()
