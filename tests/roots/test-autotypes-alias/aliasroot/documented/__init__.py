"""The only module this test root documents.

This stands in for ``lsst.images``: it annotates its own API with the
external package's plain-assignment alias, importing that package at
runtime (so its modules are in ``sys.modules`` for the registry scan) while
importing the alias itself only under ``TYPE_CHECKING`` — which is why the
name is bound in no documented namespace and Sphinx renders the annotation
from its source text, emitting the alias's bare name as a reference.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aliasroot.external import read_path

from .helpers import default_root

if TYPE_CHECKING:
    from aliasroot.external import PathExpression

__all__ = ["Loader"]


class Loader:
    """A documented class annotated with the external package's alias."""

    def load(self, path: PathExpression):  # noqa: ANN201
        """Load the bytes at *path*, which defaults into the root."""
        return read_path(path or default_root())
