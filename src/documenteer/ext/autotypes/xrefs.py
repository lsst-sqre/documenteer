"""Sphinx extension resolving (or deliberately degrading) the Python
cross-references that the autodoc ecosystem emits for typing constructs.

This is the ``documenteer.ext.autotypes.xrefs`` sub-extension of
`documenteer.ext.autotypes`; it is the project's cross-reference
resolution policy:

- It resolves cross-references that autodoc, sphinx-autodoc-typehints, and
  autodoc-pydantic emit for type aliases and other objects under names that
  don't exactly match a documented target: bare alias names from field
  annotations, private-module paths for objects re-exported from a public
  package, and role mismatches (a ``py:class`` reference to a ``py:data``
  or ``py:type`` target, locally or in an intersphinx inventory).

- References to module-level :class:`typing.TypeVar` instances,
  undocumented ``Annotated`` aliases, importable objects from external
  packages absent from every intersphinx inventory, and targets mangled
  by a leaked ``repr()`` (autodoc-pydantic renders ``Annotated`` field
  metadata such as lambdas and enum members into cross-reference
  targets) degrade to unlinked literal text instead of nitpick warnings,
  since there is never a meaningful target for them. Bare names in a
  docstring inherited from an external base class (``ConfigDict`` in
  ``pydantic.BaseModel.model_config``'s docstring) are found through the
  documented class's MRO, so they degrade the same way.

- Modules documented with ``automodapi::`` and ``:no-main-docstr:`` get a
  ``py:module`` cross-reference target pointing at the page (automodapi
  skips the ``automodule`` directive in that case, so the module otherwise
  has no target).
"""

from __future__ import annotations

import contextlib
import importlib
import inspect
import re
import typing
from typing import TYPE_CHECKING, Any, TypeAliasType, TypeVar, cast

from sphinx.ext.intersphinx import InventoryAdapter
from sphinx.util.nodes import make_refnode
from sphinx.util.typing import ExtensionMetadata

from ...version import __version__
from ._shared import _is_annotated_alias

if TYPE_CHECKING:
    from docutils import nodes
    from sphinx.addnodes import pending_xref
    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment

__all__ = ["setup"]

_ENV_MODULE_PAGES_ATTR = "documenteer_autotypes_module_pages"

_AUTOMODAPI_PATTERN = re.compile(
    r"^\.\.\s+automodapi::\s*(?P<mod>[A-Za-z0-9_.]+)\s*$"
    r"(?P<options>(?:\n\s+:[a-zA-Z_\-]+:.*$)*)",
    flags=re.MULTILINE,
)


def _record_automodapi_module_pages(
    app: Sphinx, docname: str, source: list[str]
) -> None:
    """Record modules documented via ``automodapi`` with ``:no-main-docstr:``.

    automodapi omits the ``automodule`` directive for those modules, so no
    ``py:module`` target is ever created and every reference to the module
    itself becomes a nitpick warning. This runs before automodapi's own
    ``source-read`` handler rewrites the directive away.
    """
    pages = getattr(app.env, _ENV_MODULE_PAGES_ATTR, None)
    if pages is None:
        pages = {}
        setattr(app.env, _ENV_MODULE_PAGES_ATTR, pages)
    for match in _AUTOMODAPI_PATTERN.finditer(source[0]):
        if "no-main-docstr" in match.group("options"):
            pages[match.group("mod")] = docname


_typing_registry_cache: dict[int, dict[str, list[Any]]] = {}


def _collect_type_params(obj: Any, registry: dict[str, list[Any]]) -> None:
    """Record an object's PEP 695 scoped type parameters in the registry."""
    try:
        params = getattr(obj, "__type_params__", None)
    except Exception:
        # Attribute probes on arbitrary objects can raise anything
        # (Pydantic's mock validators raise PydanticUserError).
        return
    if not isinstance(params, tuple):
        return
    for param in params:
        name = getattr(param, "__name__", None)
        if name:
            registry.setdefault(name, []).append(param)


def _project_typing_registry(env: BuildEnvironment) -> dict[str, list[Any]]:
    """Map bare names to TypeVar/alias objects found in project modules.

    Autodoc has already imported every documented module (and, through
    them, the private modules where TypeVars and aliases are actually
    defined), so ``sys.modules`` is scanned for modules under the same
    top-level packages as the documented modules. This lets a bare
    reference like ``T`` — whose defining module is not recoverable from
    the reference node — be recognized as a TypeVar.
    """
    import sys  # noqa: PLC0415

    key = id(env)
    cached = _typing_registry_cache.get(key)
    if cached is not None:
        return cached
    domain_data = env.domaindata.get("py", {})
    roots = {name.split(".")[0] for name in domain_data.get("modules", {})}
    roots.update(name.split(".")[0] for name in domain_data.get("objects", {}))
    roots.update(
        name.split(".")[0] for name in getattr(env, _ENV_MODULE_PAGES_ATTR, {})
    )
    registry: dict[str, list[Any]] = {}
    for modname, module in list(sys.modules.items()):
        top = modname.split(".")[0]
        if top not in roots:
            continue
        try:
            attrs = dict(vars(module))
        except TypeError:
            continue
        for attr, value in attrs.items():
            if attr.startswith("_"):
                continue
            if isinstance(value, (TypeVar, TypeAliasType)) or (
                _is_annotated_alias(value)
            ):
                registry.setdefault(attr, []).append(value)
                continue
            # PEP 695 scoped type parameters (``def f[U, V](...)`` /
            # ``class C[T]``) are not module attributes, but they are
            # referenced from docstrings just like module-level TypeVars.
            _collect_type_params(value, registry)
            if isinstance(value, type):
                # Snapshot: attribute access on Pydantic models can
                # mutate the class __dict__ (deferred model rebuilds).
                for member in list(vars(value).values()):
                    _collect_type_params(
                        getattr(member, "__func__", member), registry
                    )
    _typing_registry_cache.clear()
    _typing_registry_cache[key] = registry
    return registry


def _import_from_module(modname: str, attrname: str) -> Any | None:
    """Import ``modname`` and return its ``attrname`` attribute, or None."""
    try:
        module = importlib.import_module(modname)
        return getattr(module, attrname, None)
    except Exception:
        return None


def _walk_attributes(obj: Any, attrs: list[str]) -> Any | None:
    """Follow a chain of attribute accesses, or return None."""
    for attr in attrs:
        if obj is None:
            return None
        try:
            obj = getattr(obj, attr, None)
        except Exception:
            return None
    return obj


def _lookup_in_module_context(target: str, module_context: str) -> Any | None:
    """Resolve a bare or module-relative name against a documented module."""
    head, *rest = target.split(".")
    parts = module_context.split(".")
    for i in range(len(parts), 0, -1):
        obj = _walk_attributes(
            _import_from_module(".".join(parts[:i]), head), rest
        )
        if obj is not None:
            return obj
    return None


def _lookup_class_object(
    module_context: str | None, class_context: str | None
) -> type | None:
    """Import the class a reference node was rendered inside of."""
    if not module_context or not class_context:
        return None
    head, *rest = class_context.split(".")
    obj = _walk_attributes(_import_from_module(module_context, head), rest)
    return obj if isinstance(obj, type) else None


def _lookup_in_class_mro(name: str, cls: type) -> Any | None:
    """Resolve a bare name in the namespaces of a class's MRO.

    A docstring inherited from an external base class (autodoc's
    ``autodoc_inherit_docstrings``, and the MRO walk that finds attribute
    docstrings) is rendered on the subclass's page, where the ``py:module``
    context is the package being documented — a namespace that never
    imported the names the base class's own module writes about.
    ``pydantic.BaseModel.model_config``'s docstring, which refers to a
    bare ``ConfigDict``, is the canonical case: it surfaces on every model
    page while ``ConfigDict`` is importable only from Pydantic's own
    modules. Each class in the MRO contributes its defining module's
    namespace, so the reference is resolved where its docstring was
    written.

    ``builtins`` is skipped: every MRO ends at :class:`object`, so
    without the skip any bare name that collides with a builtin
    (``input``, ``dict``, ``min``, ...) would resolve here and silently
    de-warn a potential typo. Skipping keeps this rung consistent with
    the module-level contexts, where builtin-colliding bare names already
    warn when no Python intersphinx inventory is configured, and leaves
    linking real builtins to intersphinx.
    """
    import sys  # noqa: PLC0415

    try:
        mro = cls.__mro__
    except Exception:
        return None
    for base in mro:
        modname = getattr(base, "__module__", None)
        if not isinstance(modname, str) or not modname:
            continue
        if modname == "builtins":
            continue
        module = sys.modules.get(modname)
        if module is None:
            continue
        try:
            obj = getattr(module, name, None)
        except Exception:
            obj = None
        if obj is not None:
            return obj
    return None


def _lookup_runtime_object(
    target: str,
    module_context: str | None,
    class_context: str | None = None,
) -> Any | None:
    """Find the runtime object a dotted or bare reference points at."""
    if "." in target:
        modname, attrname = target.rsplit(".", 1)
        obj = _import_from_module(modname, attrname)
        if obj is not None:
            return obj
    if module_context:
        # Bare name in the context of a documented module, or a name
        # relative to it.
        obj = _lookup_in_module_context(target, module_context)
        if obj is not None:
            return obj
    if "." not in target:
        # A bare name from a docstring written in an external base class's
        # own module, inherited onto this page.
        cls = _lookup_class_object(module_context, class_context)
        if cls is not None:
            return _lookup_in_class_mro(target, cls)
    return None


def _is_unlinkable_typing_object(obj: Any) -> bool:
    """Return True for objects that never have a documentation target."""
    from typing import ParamSpec, TypeVarTuple  # noqa: PLC0415

    if isinstance(obj, (TypeVar, ParamSpec, TypeVarTuple)):
        return True
    if isinstance(obj, TypeAliasType):
        # A PEP 695 alias *should* be documented; only degrade if it was
        # not (the caller tries linking first).
        return True
    # Assignment-style Annotated aliases (SerializableXY = Annotated[...]).
    return _is_annotated_alias(obj)


def _is_external_runtime_object(env: BuildEnvironment, obj: Any) -> bool:
    """Return True when *obj* is defined outside this project's modules."""
    if inspect.ismodule(obj):
        modname = getattr(obj, "__name__", None)
    else:
        modname = getattr(obj, "__module__", None)
    if not isinstance(modname, str) or not modname:
        return False
    modules = set(env.domaindata.get("py", {}).get("modules", {}))
    modules.update(getattr(env, _ENV_MODULE_PAGES_ATTR, {}))
    return not any(
        modname == mod or modname.startswith(f"{mod}.") for mod in modules
    )


def _candidate_names(target: str) -> list[str]:
    """Generate public-path candidates for a dotted reference target.

    Objects are frequently referenced by the private module path where
    they are defined (``lsst.images._geom.XY``) while being documented
    under the public package they are re-exported from (``lsst.images.XY``).
    Candidates are produced by re-anchoring the terminal name on each
    ancestor package, longest first.
    """
    parts = target.split(".")
    if len(parts) < 2:
        return []
    name = parts[-1]
    return [".".join([*parts[:i], name]) for i in range(len(parts) - 1, 0, -1)]


_PY_ROLE_FALLBACKS = (
    "py:type",
    "py:data",
    "py:class",
    "py:exception",
    "py:function",
    "py:attribute",
    "py:pydantic_model",
    "py:pydantic_settings",
    "py:pydantic_field",
    "py:pydantic_validator",
)


def _resolve_local(  # noqa: C901, PLR0912
    app: Sphinx,
    env: BuildEnvironment,
    node: pending_xref,
    contnode: nodes.Element,
    target: str,
) -> nodes.reference | None:
    """Resolve a target against this project's own Python domain objects.

    Handles role mismatches (any object type is accepted), private-path
    references, and bare names in module context, using suffix matching as
    a last resort when it is unambiguous.
    """
    domain = env.get_domain("py")
    objects = domain.objects  # type: ignore[attr-defined]
    fromdocname = node.get("refdoc")
    if not fromdocname:
        return None

    def make(name: str) -> nodes.reference:
        entry = objects[name]
        return make_refnode(
            app.builder, fromdocname, entry.docname, entry.node_id, contnode
        )

    candidates: list[str] = [target]
    module_context = node.get("py:module")
    if "." not in target and module_context:
        parts = module_context.split(".")
        candidates.extend(
            ".".join([*parts[:i], target]) for i in range(len(parts), 0, -1)
        )
    candidates.extend(_candidate_names(target))
    for name in candidates:
        if name in objects:
            return make(name)

    def unique_suffix_match(name: str) -> str | None:
        """Match a bare name against documented objects' terminal names.

        Multiple matches are allowed if they all point at the same
        anchor (autodoc-pydantic registers objects under both their
        canonical and defining-module names).
        """
        suffix = f".{name}"
        matches = [obj for obj in objects if obj.endswith(suffix)]
        anchors = {
            (objects[obj].docname, objects[obj].node_id) for obj in matches
        }
        if len(anchors) == 1:
            return min(matches, key=len)
        return None

    # Unambiguous suffix match, but only for bare names: a dotted target
    # names a specific location, and suffix-matching it could silently
    # link an external reference (``lsst.afw.image.Mask``) to an
    # unrelated local object (``lsst.images.Mask``).
    if "." not in target:
        match = unique_suffix_match(target)
        if match is not None:
            return make(match)
    else:
        # Class-relative references (``ArchiveTree.deserialize_component``):
        # resolve the head by unambiguous suffix match on documented
        # objects, then look up the rest below it.
        head, rest = target.split(".", 1)
        head_match = unique_suffix_match(head)
        if head_match is not None:
            qualified = f"{head_match}.{rest}"
            if qualified in objects:
                return make(qualified)
        # Module-relative references (``cameras.Orientation.to_legacy``
        # for ``lsst.images.cameras.Orientation.to_legacy``): match the
        # head against documented module names.
        modules = env.domaindata.get("py", {}).get("modules", {})
        head_mods = [m for m in modules if m == head or m.endswith(f".{head}")]
        if len(head_mods) == 1:
            qualified = f"{head_mods[0]}.{rest}"
            if qualified in objects:
                return make(qualified)
        # References within this project's own namespace
        # (``lsst.images.ChebyshevField`` for an object documented as
        # ``lsst.images.fields.ChebyshevField``): the project's objects
        # are all local, so an unambiguous terminal-name match is safe.
        modules = set(env.domaindata.get("py", {}).get("modules", {}))
        modules.update(getattr(env, _ENV_MODULE_PAGES_ATTR, {}))
        if any(target.startswith(f"{mod}.") for mod in modules):
            match = unique_suffix_match(target.rsplit(".", 1)[-1])
            if match is not None:
                return make(match)
    return None


def _resolve_intersphinx(
    app: Sphinx,
    env: BuildEnvironment,
    node: pending_xref,
    contnode: nodes.Element,
    target: str,
) -> nodes.reference | None:
    """Resolve a target against intersphinx inventories under any py role.

    This catches role mismatches against external inventories (a
    ``py:data`` reference to ``typing.Union``, documented as ``py:class``)
    and private-path references to re-exported external objects
    (``h5py._hl.files.File`` vs the public ``h5py.File``).
    """
    from docutils import nodes as docutils_nodes  # noqa: PLC0415

    try:
        inventory = InventoryAdapter(env).main_inventory
    except Exception:
        return None

    def make(uri: str) -> nodes.reference:
        newnode = docutils_nodes.reference("", "", internal=False, refuri=uri)
        newnode.append(contnode)
        return newnode

    candidates = [target, *_candidate_names(target)]
    for objtype in _PY_ROLE_FALLBACKS:
        try:
            entries = inventory[objtype]
        except KeyError:
            continue
        for name in candidates:
            if name not in entries:
                continue
            return make(cast("str", entries[name][2]))

    # Bare names: unique match on the terminal name across all py
    # entries of all inventories (an ``ObservationInfo`` annotation
    # reference matching only ``astro_metadata_translator.ObservationInfo``).
    if "." not in target:
        index = _intersphinx_terminal_index(env)
        uri = index.get(target)
        if uri:
            return make(uri)
    return None


_intersphinx_index_cache: dict[int, dict[str, str]] = {}


def _intersphinx_terminal_index(env: BuildEnvironment) -> dict[str, str]:
    """Index intersphinx py object URIs by unambiguous terminal name."""
    key = id(env)
    cached = _intersphinx_index_cache.get(key)
    if cached is not None:
        return cached
    index: dict[str, str] = {}
    ambiguous: set[str] = set()
    try:
        inventory = InventoryAdapter(env).main_inventory
        for objtype in _PY_ROLE_FALLBACKS:
            try:
                entries = inventory[objtype]
            except KeyError:
                continue
            for name in entries:
                terminal = name.rsplit(".", 1)[-1]
                if terminal in ambiguous:
                    continue
                uri = cast("str", entries[name][2])
                if terminal in index and index[terminal] != uri:
                    ambiguous.add(terminal)
                    del index[terminal]
                else:
                    index[terminal] = uri
    except Exception:
        index = {}
    _intersphinx_index_cache.clear()
    _intersphinx_index_cache[key] = index
    return index


_REPR_PUNCTUATION = re.compile(r"""[<>()'"]""")
"""Characters that only appear in a target through a leaked ``repr()``."""

_NON_DOTTED_NAME = re.compile(r"""[<>()'"\s]""")
"""Characters that a dotted Python name can never contain."""


def _is_mangled_target(target: str) -> bool:
    """Return True when a reference target cannot name a Python object.

    autodoc-pydantic renders the ``repr()`` of a field's ``Annotated``
    metadata into the field's type, and lambdas, enum members, and
    ``FieldInfo`` instances all stringify with punctuation that reST then
    mangles into cross-reference targets like ``lambda>)]) <pkg.Model.field``
    or ``FieldInfo(annotation=NoneType, default_factory=<lambda>)``. Those
    can never be linked, so they should degrade to unlinked literal text
    rather than warn.

    A parameterized reference (``Model[Any]``, ``dict[str, int]``) is
    resolved by its base name, so only the base has to be a dotted name;
    repr punctuation anywhere — including inside the subscript — still means
    the whole target came from a ``repr()``. Genuine mistakes (a typo'd
    module path) stay dotted-name-shaped and keep warning.

    That breadth is a deliberate tradeoff. Quotes anywhere in the full
    target count, so a napoleon type field shaped like ``Literal['a']``
    degrades to unlinked literal text rather than linking its
    ``Literal`` base to intersphinx. Robust repr-leak detection is worth
    more than that one link, and neither outcome emits a warning.
    """
    base = target.partition("[")[0]
    return bool(
        _NON_DOTTED_NAME.search(base) or _REPR_PUNCTUATION.search(target)
    )


def _strip_bogus_typing_prefix(base: str) -> str:
    """Strip a bogus ``typing.`` prefix from a reference target.

    sphinx-autodoc-typehints qualifies :pep:`695` scoped type parameters
    (``class PublishedList[P: EventPayload]``) with a ``typing.`` prefix,
    emitting targets such as ``typing.P`` that no member of the module
    matches. Reducing those to the bare parameter name lets the ordinary
    bare-name handling apply — most importantly the project typing
    registry, which knows scoped type parameters and degrades them to
    unlinked literal text.

    Genuine ``typing`` members (``typing.Union``, ``typing.Annotated``)
    are attributes of the module and are returned unchanged, so their
    resolution against intersphinx is untouched.
    """
    prefix, _, name = base.partition(".")
    if prefix != "typing" or not name or "." in name:
        return base
    if hasattr(typing, name):
        return base
    return name


def _missing_reference(  # noqa: C901, PLR0912
    app: Sphinx,
    env: BuildEnvironment,
    node: pending_xref,
    contnode: nodes.Element,
) -> nodes.Element | None:
    """Resolve or degrade Python references that Sphinx could not."""
    if node.get("refdomain") != "py":
        return None
    target = node.get("reftarget")
    if not target:
        return None

    # Targets carrying leaked ``repr()`` punctuation: unlinked literal, not
    # a warning. This runs before any resolution attempt so that a mangled
    # target whose base happens to be linkable (``typing.Annotated[bool,
    # FieldInfo(...)]``) does not become a link whose text is the repr.
    if _is_mangled_target(target):
        return contnode

    # Parameterized references (``Model[Any]``) resolve by their base name.
    base = target.split("[", 1)[0].strip()
    if not base:
        return None

    # ``__builtins__.range``-style docstring references: resolve the
    # builtin by its bare name.
    if base.startswith(("__builtins__.", "builtins.")):
        base = base.rsplit(".", 1)[-1]

    # ``typing.P`` for a PEP 695 scoped type parameter: resolve as the
    # bare name the parameter is actually known by.
    base = _strip_bogus_typing_prefix(base)

    resolved = _resolve_local(app, env, node, contnode, base)
    if resolved is not None:
        return resolved

    resolved = _resolve_intersphinx(app, env, node, contnode, base)
    if resolved is not None:
        return resolved

    # Module documented by automodapi with :no-main-docstr:.
    pages = getattr(env, _ENV_MODULE_PAGES_ATTR, {})
    if base in pages:
        fromdocname = node.get("refdoc")
        if fromdocname:
            with contextlib.suppress(Exception):
                return make_refnode(
                    app.builder, fromdocname, pages[base], "", contnode
                )

    # Dunder members referenced from rendered alias values
    # (``XY.__get_pydantic_core_schema__``) are never documented:
    # unlinked literal, not a warning.
    terminal = base.rsplit(".", 1)[-1]
    if terminal.startswith("__") and terminal.endswith("__"):
        return contnode

    # TypeVars and undocumented aliases: unlinked literal, not a warning.
    obj = _lookup_runtime_object(
        base, node.get("py:module"), node.get("py:class")
    )
    if obj is not None and _is_unlinkable_typing_object(obj):
        return contnode
    if "." not in base:
        found = _project_typing_registry(env).get(base)
        if found and all(_is_unlinkable_typing_object(o) for o in found):
            return contnode

    # An importable object from an external package (``HttpUrl`` in a
    # pydantic field annotation): local and intersphinx resolution have
    # already failed, so no inventory documents it and nothing can ever
    # link it. Unlinked literal, not a warning. Names that fail to import
    # (typos, uninstalled packages) still warn.
    if obj is not None and _is_external_runtime_object(env, obj):
        return contnode

    return None


def setup(app: Sphinx) -> ExtensionMetadata:
    """Set up the autotypes cross-reference sub-extension."""
    # Run before sphinx-automodapi's own source-read handler (priority 500)
    # rewrites the automodapi directives away.
    app.connect("source-read", _record_automodapi_module_pages, priority=400)
    # Run after intersphinx's missing-reference handler (priority 500).
    app.connect("missing-reference", _missing_reference, priority=700)

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
