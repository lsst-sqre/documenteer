"""A public module of the documented package that nothing documents.

The plain-assignment alias here is this project's *own*, under a wholly
public module path: the "should be documented as a ``py:data``/``py:type``
object but isn't" case, which the external gate deliberately leaves
warning. It is the reason that gate tests the module an alias was found in
rather than merely recording that the alias is a union.
"""

from __future__ import annotations

from pathlib import Path

LocalAlias = str | Path
"""A union alias in one of this project's own public module paths."""


def default_root() -> Path:
    """Return the directory relative paths are resolved against."""
    return Path()
