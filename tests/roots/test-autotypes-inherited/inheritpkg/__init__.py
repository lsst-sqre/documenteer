"""The package this test root documents.

``StampFormatter`` subclasses an external base class and overrides one of
its methods without writing a docstring for the override, which is the
shape that makes autodoc inherit the base class's docstring — bare
cross-references and all.
"""

from __future__ import annotations

from extpkg import Formatter

__all__ = ["StampFormatter"]


class StampFormatter(Formatter):
    """A formatter for stamps, backed by an external base class."""

    def write_local_file(self, path: str) -> None:
        # No docstring: autodoc inherits ``Formatter.write_local_file``'s,
        # whose bare ``to_bytes`` reference is then rendered in this
        # class's context.
        raise NotImplementedError
