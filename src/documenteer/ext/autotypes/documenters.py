"""Sphinx extension rendering modern Python typing constructs in API
reference documentation.

This is the ``documenteer.ext.autotypes.documenters`` sub-extension of
`documenteer.ext.autotypes`; it covers how typing constructs are
*rendered* by autodoc:

- On Sphinx 8, it backports autodoc support for :pep:`695` type aliases by
  registering an ``autotype`` documenter that renders a ``py:type`` directive
  (Sphinx 9 provides this natively). The alias's value is rendered in the
  signature and a docstring written below the ``type`` statement is picked
  up from the module source.

- On Sphinx 9, which documents aliases natively, it overrides the native
  ``autotype`` directive to add that same docstring support.

- An ``Annotated`` alias documented by ``autodata``, and a
  ``TypeAliasType`` documented as data, inherit ``typing``'s own generic
  docstrings; those are replaced with the docstring written below the
  alias's assignment in the source — even when the alias is documented
  from a public re-export location rather than its defining module.
"""

from __future__ import annotations

import ast
import contextlib
import importlib
import inspect
from typing import TYPE_CHECKING, Any, TypeAliasType

from sphinx.util.docstrings import prepare_docstring
from sphinx.util.typing import ExtensionMetadata, stringify_annotation

from ...version import __version__
from ._shared import SPHINX_LT_9, _is_annotated_alias

if TYPE_CHECKING:
    from sphinx.application import Sphinx

__all__ = ["setup"]


def _stringify_alias_value(alias: TypeAliasType) -> str | None:
    """Render a type alias's value for a ``py:type`` ``:canonical:`` option.

    The rendered string is re-parsed as a Python annotation expression by
    the ``py:type`` directive, so it must be valid Python source (the
    "smart" ``~``-prefix form is not usable here).
    """
    try:
        return stringify_annotation(
            alias.__value__, "fully-qualified-except-typing"
        )
    except Exception:
        return None


def _find_alias_docstring(alias: TypeAliasType) -> str | None:
    """Find the docstring literal below a ``type`` statement in source.

    A string literal placed after a ``type X = ...`` statement is a
    documentation convention (matching module attributes) but is not bound
    to ``__doc__`` at runtime, so it is recovered from the module's AST.
    """
    modname = alias.__module__
    if not modname:
        return None
    try:
        module = importlib.import_module(modname)
        source = inspect.getsource(module)
        tree = ast.parse(source)
    except Exception:
        return None
    body = tree.body
    for i, node in enumerate(body):
        if (
            isinstance(node, ast.TypeAlias)
            and isinstance(node.name, ast.Name)
            and node.name.id == alias.__name__
            and i + 1 < len(body)
        ):
            nxt = body[i + 1]
            if isinstance(nxt, ast.Expr) and isinstance(
                nxt.value, ast.Constant
            ):
                value = nxt.value.value
                if isinstance(value, str):
                    return value
    return None


def _find_assignment_docstring(modname: str, name: str) -> str | None:
    """Find the docstring below a module-level assignment in source.

    Sphinx's module analyzer only records these "attribute docstrings"
    for the module autodoc is currently documenting, so an alias
    documented from its public re-export location (``lsst.images.X``)
    loses the docstring written in its defining module.
    """
    try:
        module = importlib.import_module(modname)
        source = inspect.getsource(module)
        tree = ast.parse(source)
    except Exception:
        return None
    body = tree.body
    for i, node in enumerate(body):
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
        if not any(isinstance(t, ast.Name) and t.id == name for t in targets):
            continue
        if i + 1 < len(body):
            nxt = body[i + 1]
            if isinstance(nxt, ast.Expr) and isinstance(
                nxt.value, ast.Constant
            ):
                value = nxt.value.value
                if isinstance(value, str):
                    return value
    return None


_GENERIC_TYPING_DOC_MARKERS = (
    "Runtime representation of an annotated type.",
    "Type alias.",
)


def _process_autodoc_docstring(  # noqa: C901
    app: Sphinx,
    what: str,
    name: str,
    obj: Any,
    options: Any,
    lines: list[str],
) -> None:
    """Replace generic typing docstrings on aliases with source docstrings.

    An ``Annotated`` alias documented by ``autodata`` inherits
    ``typing.Annotated``'s own docstring, and a ``TypeAliasType``
    documented as data inherits ``typing.TypeAliasType``'s. When that
    happens, look for a docstring literal below the alias's assignment —
    first in the module it is being documented from, then in the module
    where its underlying type is defined.
    """
    if what not in {"data", "attribute", "type"}:
        return
    is_generic = bool(lines) and lines[0].strip().startswith(
        _GENERIC_TYPING_DOC_MARKERS
    )
    if not (is_generic or not lines):
        return
    if not (_is_annotated_alias(obj) or isinstance(obj, TypeAliasType)):
        return
    modname, _, terminal = name.rpartition(".")
    if not modname:
        return
    candidate_modules = [modname]
    origin_module = getattr(
        getattr(obj, "__origin__", None), "__module__", None
    )
    if origin_module:
        candidate_modules.append(origin_module)
    if isinstance(obj, TypeAliasType) and obj.__module__:
        candidate_modules.append(obj.__module__)
    for candidate in candidate_modules:
        docstring = _find_assignment_docstring(candidate, terminal)
        if docstring is None and isinstance(obj, TypeAliasType):
            with contextlib.suppress(Exception):
                docstring = _find_alias_docstring(obj)
        if docstring is not None:
            lines[:] = [*prepare_docstring(docstring), ""]
            return
    if is_generic:
        # Better no docstring than typing's own documentation.
        lines[:] = []


def _setup_type_alias_documenter(app: Sphinx) -> None:
    """Register an ``autotype`` documenter for :pep:`695` type aliases.

    On Sphinx 8, an alias falls through to ``autodata``, rendering as
    ``Name = Name`` followed by the docstring of ``typing.TypeAliasType``
    itself; this documenter emits a proper ``py:type`` directive instead
    (the directive itself exists in Sphinx 8.2), and because it is
    registered with autodoc, ``sphinx.ext.autosummary.get_documenter`` —
    and therefore sphinx-automodapi stub generation — picks it up
    automatically. Sphinx 9 documents aliases natively, but does not yet
    pick up a docstring written below the ``type`` statement, so this
    documenter (registered through the legacy documenter bridge)
    overrides the native ``autotype`` directive there too.
    """
    from sphinx.ext.autodoc import ModuleLevelDocumenter  # noqa: PLC0415

    class TypeAliasDocumenter(ModuleLevelDocumenter):
        """Document a :pep:`695` ``type`` alias as a ``py:type``."""

        objtype = "type"
        directivetype = "type"
        priority = 30  # above DataDocumenter (-10)

        @classmethod
        def can_document_member(
            cls,
            member: Any,
            membername: str,
            isattr: bool,  # noqa: FBT001
            parent: Any,
        ) -> bool:
            return isinstance(member, TypeAliasType)

        def add_directive_header(self, sig: str) -> None:
            super().add_directive_header(sig)
            value = _stringify_alias_value(self.object)
            if value:
                self.add_line(f"   :canonical: {value}", self.get_sourcename())

        def document_members(
            self,
            all_members: bool = False,  # noqa: FBT001, FBT002
        ) -> None:
            # Type aliases have no members.
            pass

        def get_doc(self) -> list[list[str]] | None:
            # The runtime object's __doc__ is typing.TypeAliasType's own
            # docstring; only a docstring written in the module source
            # below the type statement is meaningful.
            docstring = _find_alias_docstring(self.object)
            if docstring:
                return [prepare_docstring(docstring)]
            return []

    if SPHINX_LT_9:
        app.add_autodocumenter(TypeAliasDocumenter)
    else:
        # Sphinx 9 registers a native autotype directive from a
        # config-inited handler — after extension setup — so registering
        # a directive here would only provoke an "already registered"
        # warning from that handler and get overwritten anyway. Register
        # just the documenter now, and install the legacy dispatching
        # directive after autodoc's handler has run.
        app.registry.add_documenter("type", TypeAliasDocumenter)

        def _register_autotype(app: Sphinx, config: Any) -> None:
            from sphinx.ext.autodoc.directive import (  # noqa: PLC0415
                AutodocDirective,
            )

            app.add_directive("autotype", AutodocDirective, override=True)

        app.connect("config-inited", _register_autotype, priority=900)


def setup(app: Sphinx) -> ExtensionMetadata:
    """Set up the autotypes documenters sub-extension."""
    # Requires autodoc to be set up first.
    app.setup_extension("sphinx.ext.autodoc")
    # On Sphinx 8 this provides the ``autotype`` directive (which only
    # exists natively from Sphinx 9); on Sphinx 9 it overrides the native
    # directive, which does not yet support docstrings written below
    # ``type`` statements.
    _setup_type_alias_documenter(app)
    app.connect("autodoc-process-docstring", _process_autodoc_docstring)

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
