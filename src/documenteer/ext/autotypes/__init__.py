"""Sphinx extension bridging gaps in the autodoc/automodapi ecosystem for
modern Python typing constructs.

This extension improves Python API reference generation for projects that
use :pep:`695` type aliases (``type X = ...``), module-level type variables,
and Pydantic models together with sphinx-automodapi. It is an umbrella over
three sub-extensions, each a Sphinx extension in its own right that can also
be enabled individually:

``documenteer.ext.autotypes.documenters``
    Rendering: how autodoc documents :pep:`695` type aliases and
    ``Annotated`` aliases, including the docstrings written below their
    statements in the source.

``documenteer.ext.autotypes.compat``
    Temporary compatibility shims for other packages in the ecosystem
    (sphinx-automodapi, sphinx-click). This module aspires to delete
    itself as those upstreams ship fixes.

``documenteer.ext.autotypes.xrefs``
    Cross-reference policy: resolving the Python references that the
    autodoc ecosystem emits under names that don't match a documented
    target, and degrading references that can never have a target — type
    variables, external objects no inventory covers, objects reachable
    only under private module paths — to unlinked literal text instead of
    nitpick warnings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sphinx.util.typing import ExtensionMetadata

from ...version import __version__

if TYPE_CHECKING:
    from sphinx.application import Sphinx

__all__ = ["setup"]


def setup(app: Sphinx) -> ExtensionMetadata:
    """Set up the autotypes extension and all of its sub-extensions."""
    app.setup_extension("documenteer.ext.autotypes.documenters")
    app.setup_extension("documenteer.ext.autotypes.compat")
    app.setup_extension("documenteer.ext.autotypes.xrefs")

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
