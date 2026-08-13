"""Sphinx extension carrying temporary compatibility shims for the
autodoc/automodapi ecosystem.

This is the ``documenteer.ext.autotypes.compat`` sub-extension of
`documenteer.ext.autotypes`, and it aspires to delete itself. Every patch
here works around a bug or a gap in another package, and each one should
be removed once its upstream home ships a fix:

- ``sphinx_automodapi.utils.get_object_type`` ignores third-party autodoc
  documenters on Sphinx 9 (upstream: sphinx-automodapi).

- ``sphinx_automodapi.utils.find_mod_objs`` mis-derives the module of an
  assignment-style ``Annotated`` alias, so automodapi's ``onlylocals`` filter
  drops aliases its own summary table lists (upstream: sphinx-automodapi).

- ``sphinx_click.ext.mock`` can end up bound to the
  ``sphinx.ext.autodoc.mock`` *module* instead of the ``mock()`` context
  manager on Sphinx 9 (upstream: sphinx-click).

- Sphinx 9 crashes formatting the signature of a callable ``data`` or
  ``attribute`` object when another extension supplies one, dropping the
  object from the built documentation (upstream: sphinx, with
  sphinx-autodoc-typehints as the trigger).

- Sphinx 9 leaves its own built-in documenters out of the legacy
  class-based registry, so a third-party legacy documenter — most
  importantly autodoc-pydantic's model documenter — finds nothing able to
  document an ordinary method, property, or attribute and drops those
  members from the page (upstream: sphinx, with autodoc-pydantic as the
  trigger).

Nothing else in Documenteer should depend on this module: it exists only
so that the rest of `documenteer.ext.autotypes` can assume a working
ecosystem.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sphinx.util.typing import ExtensionMetadata

from ...version import __version__
from ._shared import SPHINX_LT_9, _is_annotated_alias

if TYPE_CHECKING:
    from sphinx.application import Sphinx

__all__ = ["setup"]


def _patch_automodapi_object_types() -> None:  # noqa: C901
    """Restore third-party documenter selection in sphinx-automodapi.

    On Sphinx 9, ``sphinx_automodapi.utils.get_object_type`` uses Sphinx's
    internal ``_get_documenter``, which only knows built-in object types.
    Third-party documenters registered through ``app.add_autodocumenter``
    (autodoc-pydantic's ``pydantic_model`` most importantly) are ignored,
    so automodapi generates generic ``autoclass`` stubs listing every
    inherited ``BaseModel`` member. This patch consults the autodoc
    registry first, considering only non-Sphinx documenters so that
    Sphinx 9's improved native classification (e.g. ``type`` for alias
    objects) is preserved.
    """
    try:
        from sphinx_automodapi import utils  # noqa: PLC0415
    except ImportError:
        return

    if getattr(utils.get_object_type, "_documenteer_autotypes", False):
        return

    original = utils.get_object_type

    def get_object_type(app: Sphinx | None, obj: Any, parent: Any) -> str:
        if app is not None:
            try:
                documenters = list(app.registry.documenters.values())
            except AttributeError:
                documenters = []
            candidates = []
            for documenter in documenters:
                if documenter.__module__.startswith(
                    ("sphinx.", "documenteer.")
                ):
                    continue
                try:
                    if documenter.can_document_member(obj, "", False, parent):
                        candidates.append(documenter)
                except Exception:  # noqa: S110
                    pass
            if candidates:
                best = max(candidates, key=lambda d: d.priority)
                return best.objtype
        return original(app, obj, parent)

    get_object_type._documenteer_autotypes = True  # type: ignore[attr-defined]  # noqa: SLF001
    utils.get_object_type = get_object_type


def _patch_find_mod_objs() -> None:
    """Fix sphinx-automodapi's locality test for ``Annotated`` aliases.

    A pre-PEP 695, assignment-style alias like
    ``SerializableXY = Annotated[XY[T], ...]`` has
    ``__module__ == 'typing'`` and ``__name__ == 'Annotated'``, so
    ``find_mod_objs`` derives the fully-qualified name ``typing.Annotated``
    and the ``onlylocals`` filter used during automodapi stub generation
    drops it — while the summary table (built without ``onlylocals``)
    still lists it. The result is a toctree entry with no stub file and
    an autosummary warning. This patch derives such an alias's name from
    where it is being documented instead.
    """
    try:
        from sphinx_automodapi import (  # noqa: PLC0415
            automodapi,
            automodsumm,
            utils,
        )
    except ImportError:
        return

    if getattr(utils.find_mod_objs, "_documenteer_autotypes", False):
        return

    original = utils.find_mod_objs

    def find_mod_objs(
        modname: str,
        onlylocals: bool | list[str] = False,  # noqa: FBT001, FBT002
        sort: bool = False,  # noqa: FBT001, FBT002
    ) -> tuple[list[str], list[str], list[Any]]:
        import sys  # noqa: PLC0415

        localnames, fqnames, objs = original(
            modname, onlylocals=False, sort=sort
        )
        fqnames = [
            f"{modname}.{lnm}" if _is_annotated_alias(obj) else fqn
            for lnm, fqn, obj in zip(localnames, fqnames, objs, strict=True)
        ]
        # Reproduce the original onlylocals filtering (skipped when the
        # module declares __all__, matching upstream behavior).
        if onlylocals and not hasattr(sys.modules[modname], "__all__"):
            prefixes = (
                tuple(onlylocals)
                if isinstance(onlylocals, (tuple, list))
                else (modname,)
            )
            valids = [fqn.startswith(prefixes) for fqn in fqnames]
            localnames = [
                e for e, v in zip(localnames, valids, strict=True) if v
            ]
            fqnames = [e for e, v in zip(fqnames, valids, strict=True) if v]
            objs = [e for e, v in zip(objs, valids, strict=True) if v]
        return localnames, fqnames, objs

    find_mod_objs._documenteer_autotypes = True  # type: ignore[attr-defined]  # noqa: SLF001
    utils.find_mod_objs = find_mod_objs
    # The automodapi modules bind find_mod_objs at import time.
    automodapi.find_mod_objs = find_mod_objs
    automodsumm.find_mod_objs = find_mod_objs


def _patch_sphinx_click_mock(app: Sphinx) -> None:
    """Repair sphinx-click's ``mock`` import under Sphinx 9.

    sphinx-click does ``from sphinx.ext.autodoc import mock``. On Sphinx 9
    ``sphinx.ext.autodoc.mock`` is also a submodule, and once any other
    extension imports that submodule, the package attribute is rebound to
    the module — so sphinx-click can end up holding the module instead of
    the ``mock()`` context manager and every ``click`` directive fails
    with ``TypeError: 'module' object is not callable``.
    """
    try:
        import importlib  # noqa: PLC0415
        import inspect as inspect_module  # noqa: PLC0415

        import sphinx_click.ext as click_ext  # noqa: PLC0415

        if inspect_module.ismodule(click_ext.mock):
            mock_module = importlib.import_module("sphinx.ext.autodoc.mock")
            click_ext.mock = mock_module.mock
    except Exception:  # noqa: S110
        pass


def _restore_legacy_member_documenters(app: Sphinx) -> None:
    """Keep non-field members on autodoc-pydantic model pages on Sphinx 9.

    autodoc-pydantic's model documenter subclasses autodoc's legacy
    class-based ``ClassDocumenter``, whose ``document_members`` picks a
    documenter for each member by asking every class in
    ``app.registry.documenters`` whether it ``can_document_member``, and
    silently skips the member when none can. Sphinx 9 populates that
    registry with its own built-in documenters only when
    ``autodoc_use_legacy_class_based`` is enabled; by default the registry
    holds nothing but third-party entries. autodoc-pydantic's own
    documenters cover fields, validators, and config, so those survive,
    while every ordinary method, classmethod, property, and attribute
    (Safir's ``build_uws_config``, lsst.images' ``deserialize``) vanishes
    from the model page — taking prose references to it down as nitpick
    warnings, which is what forced adopters to pin ``sphinx<9``.

    Registering the built-in documenters restores the candidate pool
    without switching the build over to the legacy API: the ``autoclass``,
    ``automethod``, … directives keep dispatching to Sphinx 9's native
    implementation, because only ``Sphinx.add_autodocumenter`` rebinds
    those directive names and this registers the documenters alone.
    ``setdefault`` leaves any documenter another extension registered for
    the same object type in place, so third-party overrides still win.

    Retire this once autodoc-pydantic documents members through Sphinx 9's
    native autodoc API, or Sphinx populates the legacy registry whenever a
    legacy documenter is in use.
    """
    try:
        from sphinx.ext.autodoc import (  # noqa: PLC0415
            AttributeDocumenter,
            ClassDocumenter,
            DataDocumenter,
            DecoratorDocumenter,
            ExceptionDocumenter,
            FunctionDocumenter,
            MethodDocumenter,
            ModuleDocumenter,
            PropertyDocumenter,
        )
    except ImportError:
        return

    documenters = app.registry.documenters
    for documenter in (
        ModuleDocumenter,
        ClassDocumenter,
        ExceptionDocumenter,
        DataDocumenter,
        FunctionDocumenter,
        DecoratorDocumenter,
        MethodDocumenter,
        AttributeDocumenter,
        PropertyDocumenter,
    ):
        documenters.setdefault(documenter.objtype, documenter)


def _suppress_data_signature(
    app: Sphinx,
    what: str,
    name: str,
    obj: Any,
    options: Any,
    signature: str | None,
    return_annotation: str | None,
) -> tuple[None, None] | None:
    """Keep callable singletons from vanishing out of Sphinx 9 autodoc.

    Sphinx 9 allocates ``data`` objects no signature slot, but
    sphinx-autodoc-typehints' ``autodoc-process-signature`` handler returns
    a signature tuple for *any* annotated callable — including a
    module-level instance of a ``__call__``-defining class, the shape
    Safir's ``*_dependency`` injection helpers use. Sphinx then executes
    ``signatures[0] = ...`` against that empty list; the ``IndexError`` is
    caught and logged as ``error while formatting signature ...
    [autodoc]``, and the object is dropped from the built docs entirely.

    This listener is connected ahead of the typehints handler, and
    ``emit_firstresult`` stops at the first non-``None`` result, so
    returning ``(None, None)`` for the affected object types keeps any
    later handler from supplying a signature Sphinx has nowhere to put.
    Sphinx's own ``isinstance(result[0], str)`` guard then skips the fatal
    assignment and the object documents without a signature line — which
    is what Sphinx 9 models for a data object anyway.

    Retire this once Sphinx guards the empty-signatures assignment, or
    sphinx-autodoc-typehints stops returning signature tuples for data
    objects.
    """
    if what in {"data", "attribute"}:
        return None, None
    return None


def setup(app: Sphinx) -> ExtensionMetadata:
    """Set up the autotypes compatibility sub-extension."""
    if not SPHINX_LT_9:
        # Patch immediately: automodapi generates its stub files from a
        # builder-inited handler, which may run before any handler this
        # extension could register.
        _patch_automodapi_object_types()
        # All extensions are loaded by builder-inited, so sphinx-click's
        # import state is settled by then.
        app.connect("builder-inited", _patch_sphinx_click_mock)
        # ``autodoc-process-signature`` is autodoc's event, so autodoc has
        # to be set up before anything can listen for it.
        app.setup_extension("sphinx.ext.autodoc")
        # Fill the legacy documenter registry now rather than from an
        # event: ``setdefault`` never displaces a documenter another
        # extension registers, whenever that extension's setup runs.
        _restore_legacy_member_documenters(app)
        # Priority below the default 500 so this runs before
        # sphinx-autodoc-typehints' own handler.
        app.connect(
            "autodoc-process-signature", _suppress_data_signature, priority=400
        )
    _patch_find_mod_objs()

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
