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
  or ``py:type`` target, locally or in an intersphinx inventory). A bare
  name that a docstring inherited from an external base class writes
  about one of that base's own members (``to_bytes`` in
  ``FormatterV2.write_local_file``'s docstring) is retried under the
  defining class's fully-qualified name, which the base project's
  inventory does cover.

- References to module-level :class:`typing.TypeVar` instances,
  undocumented ``Annotated`` aliases, importable objects from external
  packages absent from every intersphinx inventory, objects this project
  defines only under private module paths, and targets mangled by a
  leaked ``repr()`` (autodoc-pydantic renders ``Annotated`` field
  metadata such as lambdas and enum members into cross-reference
  targets) degrade to unlinked literal text instead of nitpick warnings,
  since there is never a meaningful target for them. Bare names in a
  docstring inherited from an external base class (``ConfigDict`` in
  ``pydantic.BaseModel.model_config``'s docstring) are found through the
  documented class's MRO, so they degrade the same way. A leaked
  ``repr()`` that happens to *parse* as Python is split into fragments
  instead of mangled, so the fragments of a documented class's own
  ``Annotated`` metadata (``Ge``, ``file``, ``ExecutionPhase.PENDING``)
  degrade too. Project-local objects under wholly public module paths
  keep warning: those are the ones that should be exported and
  documented, so they stay visible.

- Modules documented with ``automodapi::`` and ``:no-main-docstr:`` get a
  ``py:module`` cross-reference target pointing at the page (automodapi
  skips the ``automodule`` directive in that case, so the module otherwise
  has no target).
"""

from __future__ import annotations

import ast
import builtins
import contextlib
import dataclasses
import importlib
import inspect
import re
import typing
from typing import TYPE_CHECKING, Any, Literal, TypeAliasType, TypeVar, cast

from sphinx.ext.intersphinx import InventoryAdapter
from sphinx.util.nodes import make_refnode
from sphinx.util.typing import ExtensionMetadata, stringify_annotation

from ...version import __version__
from ._shared import _is_annotated_alias

if TYPE_CHECKING:
    from collections.abc import Sequence

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


_MISSING = object()
"""Sentinel for "this name was never seen here"."""


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

    Failing every module namespace, the MRO's classes are searched for an
    *attribute* of that name (see :func:`_lookup_mro_attribute`): an
    inherited docstring writes about its own class's members too, not
    only about the names its module imports.
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
    found = _lookup_mro_attribute(name, cls)
    return found[0] if found is not None else None


def _lookup_mro_attribute(name: str, cls: type) -> tuple[Any, str] | None:
    """Find a bare name among the attributes a class's MRO defines.

    A docstring inherited from an external base class writes about that
    base's *own* members by their bare names. ``lsst.daf.butler``'s
    ``FormatterV2.write_local_file`` is the canonical case: its docstring
    refers to a bare ``to_bytes``, and a subclass that overrides
    ``write_local_file`` without writing its own docstring inherits the
    text — bare reference and all — onto a page whose ``py:module``
    context is the subclass's package.

    :func:`_lookup_in_class_mro` cannot find those names, because they are
    attributes *of* an MRO class rather than names in any MRO class's
    defining-module namespace. This does find them, and reports the
    fully-qualified name the attribute is documented under —
    ``{module}.{qualname}.{name}`` of the class that *defines* it, not of
    the class the reference was rendered inside — so the caller can retry
    intersphinx with a name the base project's inventory can cover.

    The defining class is found through each MRO class's own ``__dict__``:
    ``getattr`` alone would report every inherited attribute against the
    documented subclass, whose name no external inventory knows.

    Names are screened against ``builtins`` twice over. Classes defined in
    the ``builtins`` module are skipped, for the reason
    :func:`_lookup_in_class_mro` skips that namespace: every MRO ends at
    :class:`object`, and a subclass of a builtin type would otherwise
    resolve bare names like ``get`` or ``items`` on its page. Bare names
    that *are* builtins are skipped as well, whichever class defines
    them: a docstring's bare ``dict`` means the builtin type, not the
    deprecated ``pydantic.BaseModel.dict`` method it happens to collide
    with, so resolving it here would both silence a possible typo and
    risk linking the reference to the wrong object entirely.
    """
    if hasattr(builtins, name):
        return None
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
        try:
            obj = getattr(base, name) if name in vars(base) else _MISSING
        except Exception:
            # Attribute access on a class can run arbitrary descriptor
            # code (Pydantic's mock validators raise PydanticUserError).
            obj = _MISSING
        if obj is _MISSING:
            continue
        qualname = getattr(base, "__qualname__", None)
        if not isinstance(qualname, str) or not qualname:
            continue
        return obj, f"{modname}.{qualname}.{name}"
    return None


_AMBIGUOUS = object()
"""Sentinel for a name that names different objects in different modules."""

_mro_namespace_cache: dict[int, dict[frozenset[str], dict[str, Any]]] = {}


def _mro_package_roots(cls: type) -> frozenset[str]:
    """Collect the top-level packages defining a class's MRO.

    ``builtins`` is excluded for the same reason
    :func:`_lookup_in_class_mro` skips it: every MRO ends at
    :class:`object`, so including it would make every bare name that
    collides with a builtin resolve on every class page.
    """
    try:
        mro = cls.__mro__
    except Exception:
        return frozenset()
    roots = set()
    for base in mro:
        modname = getattr(base, "__module__", None)
        if not isinstance(modname, str) or not modname:
            continue
        root = modname.split(".")[0]
        if root != "builtins":
            roots.add(root)
    return frozenset(roots)


def _mro_root_namespace(
    roots: frozenset[str], env: BuildEnvironment | None = None
) -> dict[str, Any]:
    """Index public names exposed by loaded modules under *roots*.

    Some names are written about in a class's docstrings — or synthesized
    into its rendered annotations — while being importable from neither
    the documented module nor any module in the class's MRO. Pydantic's
    ``FieldInfo`` is the canonical case: the annotation parser splits a
    field's rendered ``Annotated[str, FieldInfo(...)]`` type into its
    parts, emitting a bare ``FieldInfo`` reference, yet ``FieldInfo`` is
    exposed by neither the ``pydantic`` package nor ``pydantic.main`` (the
    MRO class that supplies the field page's inherited docstrings) — its
    only home is ``pydantic.fields``.

    Autodoc has already imported every module those packages pull in, so
    scanning :data:`sys.modules` under the MRO's package roots finds them.
    The scan is cached per build environment, following
    :func:`_project_typing_registry`.
    """
    import sys  # noqa: PLC0415

    key = id(env)
    by_roots = _mro_namespace_cache.get(key)
    if by_roots is None:
        _mro_namespace_cache.clear()
        by_roots = {}
        _mro_namespace_cache[key] = by_roots
    cached = by_roots.get(roots)
    if cached is not None:
        return cached
    index: dict[str, Any] = {}
    for modname, module in list(sys.modules.items()):
        if modname.split(".")[0] not in roots:
            continue
        try:
            attrs = dict(vars(module))
        except TypeError:
            continue
        for attr, value in attrs.items():
            if attr.startswith("_"):
                continue
            found = index.get(attr, _MISSING)
            if found is _MISSING:
                index[attr] = value
            elif found is not value:
                # The same name meaning different objects in different
                # modules cannot be resolved to one of them, so the
                # reference keeps warning.
                index[attr] = _AMBIGUOUS
    by_roots[roots] = index
    return index


def _lookup_in_mro_root_packages(
    name: str, cls: type, env: BuildEnvironment | None = None
) -> Any | None:
    """Resolve a bare name against the MRO's top-level packages."""
    roots = _mro_package_roots(cls)
    if not roots:
        return None
    obj = _mro_root_namespace(roots, env).get(name, _MISSING)
    if obj is _MISSING or obj is _AMBIGUOUS:
        return None
    return obj


def _lookup_runtime_object(
    target: str,
    module_context: str | None,
    class_context: str | None = None,
    env: BuildEnvironment | None = None,
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
            obj = _lookup_in_class_mro(target, cls)
            if obj is not None:
                return obj
            # Last resort: a name exposed by neither the documented module
            # nor any MRO class's own module, but by some other module of
            # the packages those classes come from.
            return _lookup_in_mro_root_packages(target, cls, env)
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


def _runtime_object_module(obj: Any) -> str | None:
    """Return the module path *obj* is defined in, or None."""
    if inspect.ismodule(obj):
        modname = getattr(obj, "__name__", None)
    else:
        modname = getattr(obj, "__module__", None)
    if not isinstance(modname, str) or not modname:
        return None
    return modname


def _is_project_local_module(env: BuildEnvironment, modname: str) -> bool:
    """Return True when *modname* is under a module this project documents."""
    modules = set(env.domaindata.get("py", {}).get("modules", {}))
    modules.update(getattr(env, _ENV_MODULE_PAGES_ATTR, {}))
    return any(
        modname == mod or modname.startswith(f"{mod}.") for mod in modules
    )


def _is_external_runtime_object(env: BuildEnvironment, obj: Any) -> bool:
    """Return True when *obj* is defined outside this project's modules."""
    modname = _runtime_object_module(obj)
    if modname is None:
        return False
    return not _is_project_local_module(env, modname)


def _is_project_private_runtime_object(
    env: BuildEnvironment, obj: Any
) -> bool:
    """Return True when *obj* lives only under a private path of this project.

    A project's own internal modules hold classes that its public API
    refers to without re-exporting: Pydantic serialization models are the
    canonical case, since a field's annotation names the model class
    defined in ``lsst.images._transforms._transform`` while the package
    exports only the public model that uses it. Sphinx 9 emits a
    ``py:class`` reference for those names — as a bare name on the field's
    page, or as a fully-qualified name with no document context at all —
    where Sphinx 8 rendered the same signature as plain text. The object
    is real and importable, but it lives where no public documentation
    target can be created, so nothing can ever link it.

    The gate is the *module path*, not the object: a project-local object
    is degraded only when some segment of its defining module path starts
    with an underscore. Project-local objects under wholly public module
    paths — the ones that should be exported and documented but aren't —
    keep warning, which is the invariant separating this rung from a
    blanket "never warn about our own objects" policy. External objects
    belong to :func:`_is_external_runtime_object`'s rung whether or not
    their own module paths are private.
    """
    modname = _runtime_object_module(obj)
    if modname is None:
        return False
    if not _is_project_local_module(env, modname):
        return False
    return any(part.startswith("_") for part in modname.split("."))


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

_PY_MEMBER_ROLE_FALLBACKS = ("py:method", "py:property", *_PY_ROLE_FALLBACKS)
"""Roles to try for a reference rebuilt as a class attribute's full name.

Methods and properties are only searched for those rebuilt names, not for
every reference: :data:`_PY_ROLE_FALLBACKS` also drives the bare terminal
name index (:func:`_intersphinx_terminal_index`), where admitting every
method name in every inventory would broaden bare-name linking well past
this rung's business.
"""


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
    objtypes: Sequence[str] = _PY_ROLE_FALLBACKS,
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
    for objtype in objtypes:
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


_STRINGIFY_MODE: Literal["fully-qualified-except-typing"] = (
    "fully-qualified-except-typing"
)
"""Rendering mode Sphinx uses for the parts of an ``Annotated`` metadata."""


def _ast_dotted_name(node: ast.AST) -> str | None:
    """Return the dotted name an AST node spells, or None.

    This mirrors Sphinx's own annotation unparser, which renders an
    ``ast.Name`` as its id and an ``ast.Attribute`` chain as one dotted
    string — and then turns each such string into a cross-reference. Any
    other node (a call, a subscript, a literal) is rendered as structure
    rather than as a reference target, so it has no name of its own.
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        value = _ast_dotted_name(node.value)
        return f"{value}.{node.attr}" if value else None
    return None


def _expression_names(node: ast.AST) -> set[str]:
    """Collect every name Sphinx's unparser would emit for *node*."""
    names: set[str] = set()
    stack: list[ast.AST] = [node]
    while stack:
        current = stack.pop()
        name = _ast_dotted_name(current)
        if name is not None:
            names.add(name)
            continue
        stack.extend(ast.iter_child_nodes(current))
    return names


def _parse_expression(text: str) -> ast.expr | None:
    """Parse *text* as a Python expression, or return None."""
    try:
        return ast.parse(text.strip(), mode="eval").body
    except (SyntaxError, ValueError, MemoryError, RecursionError):
        return None


def _is_annotated_subscript(node: ast.expr) -> bool:
    """Return True when *node* subscripts an ``Annotated`` name."""
    name = _ast_dotted_name(node)
    return name is not None and name.rsplit(".", 1)[-1] == "Annotated"


def _source_metadata_names(text: str) -> set[str]:
    """Collect the names in the metadata positions of a source annotation.

    A module that has not evaluated its annotations (``from __future__
    import annotations``, or an explicitly quoted annotation) leaves
    Sphinx rendering the annotation's own *source text*, which it then
    unparses into cross-references exactly as written. Only the elements
    after the first belong to the metadata: the first is the annotated
    type, which keeps following the ordinary resolution ladder.
    """
    tree = _parse_expression(text)
    if tree is None:
        return set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript):
            continue
        if not _is_annotated_subscript(node.value):
            continue
        subscript = node.slice
        if not isinstance(subscript, ast.Tuple):
            continue
        for element in subscript.elts[1:]:
            names |= _expression_names(element)
    return names


def _render_metadata_object(obj: Any) -> list[str]:
    """Render an ``Annotated`` metadata object the ways Sphinx renders it.

    ``sphinx.util.typing.stringify_annotation`` writes a metadata object
    into the rendered annotation as its ``repr()``, except for a
    dataclass, whose fields it stringifies one by one — so a string field
    value loses its quotes and is left looking like a bare name
    (``PathType(path_type=file)`` for Pydantic's ``FilePath``). Both
    renderings are produced, since the reference could have come from
    either.
    """

    def render(value: Any) -> str:
        return stringify_annotation(value, _STRINGIFY_MODE)

    renderings: list[str] = []
    with contextlib.suppress(Exception):
        renderings.append(repr(obj))
    if not isinstance(obj, type) and dataclasses.is_dataclass(obj):
        with contextlib.suppress(Exception):
            fields = ", ".join(
                f"{field.name}={render(getattr(obj, field.name))}"
                for field in dataclasses.fields(obj)
                if field.repr
            )
            renderings.append(f"{render(type(obj))}({fields})")
    return renderings


def _iter_annotated_metadata(value: Any, seen: set[int]) -> list[Any]:
    """Collect the metadata objects of every ``Annotated`` form in *value*.

    ``Annotated`` forms nest: Pydantic expands a ``FilePath`` field into
    ``Annotated[Annotated[Path, PathType('file')] | None, FieldInfo(...)]``,
    and Sphinx renders the metadata of both.
    """
    if id(value) in seen:
        return []
    seen.add(id(value))
    metadata = getattr(value, "__metadata__", None)
    if isinstance(metadata, tuple):
        found = list(metadata)
        origin = getattr(value, "__origin__", None)
        if origin is not None:
            found.extend(_iter_annotated_metadata(origin, seen))
        return found
    try:
        args = typing.get_args(value)
    except Exception:
        return []
    found = []
    for arg in args:
        found.extend(_iter_annotated_metadata(arg, seen))
    return found


def _class_annotation_values(cls: type) -> list[Any]:
    """Collect the annotation values Sphinx renders for a class's members.

    Both sources Sphinx itself falls back through are read: the raw
    ``__annotations__`` of every class in the MRO (which is what
    ``sphinx.util.typing.get_type_hints`` returns when evaluation fails,
    and which holds unevaluated *strings* under :pep:`563`), and the
    evaluated hints when they are available.
    """
    values: list[Any] = []
    try:
        mro = cls.__mro__
    except Exception:
        return values
    for base in mro:
        if base is object:
            continue
        try:
            annotations = vars(base).get("__annotations__")
        except TypeError:
            continue
        if isinstance(annotations, dict):
            values.extend(annotations.values())
    with contextlib.suppress(Exception):
        values.extend(typing.get_type_hints(cls, include_extras=True).values())
    return values


_annotated_fragment_cache: dict[int, dict[int, frozenset[str]]] = {}


def _annotated_metadata_fragments(
    cls: type, env: BuildEnvironment | None = None
) -> frozenset[str]:
    """Index the names a class's ``Annotated`` metadata can synthesize.

    Sphinx renders a field's ``Annotated`` metadata into the field's type
    and then unparses the result, so every name in that rendering becomes
    a cross-reference target. When the rendering is not valid Python the
    whole target is mangled and :func:`_is_mangled_target` catches it; when
    it *is* valid Python the target is split into syntactically clean
    fragments instead — a constraint class from the ``repr()`` of a
    Pydantic ``FieldInfo`` (``Ge``, ``Le``), a dataclass field's
    unquoted string value (``file``), or an enum member written into the
    metadata of a source-text annotation (``ExecutionPhase.PENDING``).

    Those fragments describe how a value is validated; they are not
    references to anything, and the first two are not even names of
    objects. Rebuilding the set of fragments *this* class can produce is
    what lets them degrade without a blanket rule that would silence
    genuine mistakes elsewhere: a name that no metadata rendering of this
    class contains is left to warn.

    The index resolves nothing, so it adds no lookup surface and no
    ambiguity question: it is consulted only after every resolution rung
    has already failed. It is cached per build environment and class,
    following :func:`_mro_root_namespace`.
    """
    key = id(env)
    by_class = _annotated_fragment_cache.get(key)
    if by_class is None:
        _annotated_fragment_cache.clear()
        by_class = {}
        _annotated_fragment_cache[key] = by_class
    cached = by_class.get(id(cls))
    if cached is not None:
        return cached
    fragments: set[str] = set()
    for value in _class_annotation_values(cls):
        if isinstance(value, str):
            fragments |= _source_metadata_names(value)
            continue
        for metadata in _iter_annotated_metadata(value, set()):
            for rendering in _render_metadata_object(metadata):
                tree = _parse_expression(rendering)
                if tree is not None:
                    fragments |= _expression_names(tree)
    result = frozenset(fragments)
    by_class[id(cls)] = result
    return result


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

    # The class the reference was rendered inside, when it names one: the
    # rungs below read its MRO and its ``Annotated`` metadata.
    cls = _lookup_class_object(node.get("py:module"), node.get("py:class"))

    # A bare name from a docstring inherited from an external base class,
    # naming one of that base's own members (``to_bytes`` in
    # ``FormatterV2.write_local_file``'s docstring, inherited onto a
    # subclass's override): the external project documents it under its
    # defining class, so retry intersphinx with the name rebuilt from the
    # MRO. The bare name on its own gets nowhere — a member name like
    # ``to_bytes`` is rarely unique across the configured inventories.
    if "." not in base and cls is not None:
        attribute = _lookup_mro_attribute(base, cls)
        if attribute is not None:
            resolved = _resolve_intersphinx(
                app,
                env,
                node,
                contnode,
                attribute[1],
                objtypes=_PY_MEMBER_ROLE_FALLBACKS,
            )
            if resolved is not None:
                return resolved

    # TypeVars and undocumented aliases: unlinked literal, not a warning.
    obj = _lookup_runtime_object(
        base, node.get("py:module"), node.get("py:class"), env
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

    # An object this project defines only under a private module path (a
    # Pydantic serialization model in ``pkg._transforms._transform``,
    # referenced by a field annotation as a bare name or as a
    # fully-qualified name with no document context at all): the object is
    # real, but no public documentation target for it can exist, so
    # nothing can ever link it. Unlinked literal, not a warning. This
    # reinterprets an object the rungs above already resolved; it does not
    # widen what resolves. Project-local objects under wholly public
    # module paths keep warning, since those should be exported and
    # documented.
    if obj is not None and _is_project_private_runtime_object(env, obj):
        return contnode

    # A fragment of an ``Annotated`` metadata expression that Sphinx wrote
    # into the field's rendered type and then unparsed: a constraint class
    # from a ``FieldInfo`` repr (``Ge``), a dataclass metadata field's
    # unquoted string value (``file``), or an enum member named by
    # attribute path in a source-text annotation
    # (``ExecutionPhase.PENDING``). These describe how a value is
    # validated rather than referring to anything, and the last rungs
    # could not resolve them because they are names in no scanned
    # namespace — or, for a value fragment, names of nothing at all.
    # Unlinked literal, not a warning. Only fragments *this* class's own
    # metadata renders count, so names from elsewhere keep warning.
    if cls is not None and base in _annotated_metadata_fragments(cls, env):
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
