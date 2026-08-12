# type: ignore
"""Tests for documenteer.ext.autotypes."""

from __future__ import annotations

import pytest
from docutils import nodes
from sphinx import addnodes
from sphinx.pycode import ModuleAnalyzer
from sphinx.testing.util import SphinxTestApp

from documenteer.ext.autotypes._shared import _is_annotated_alias
from documenteer.ext.autotypes.compat import (
    _restore_legacy_member_documenters,
    _suppress_data_signature,
)
from documenteer.ext.autotypes.documenters import (
    _find_alias_docstring,
    _find_assignment_docstring,
)
from documenteer.ext.autotypes.xrefs import (
    _AMBIGUOUS,
    _annotated_metadata_fragments,
    _candidate_names,
    _is_mangled_target,
    _is_plain_type_alias,
    _is_project_private_runtime_object,
    _is_unlinkable_registry_match,
    _lookup_mro_attribute,
    _lookup_runtime_object,
    _missing_reference,
    _mro_root_namespace,
    _project_typing_registry,
    _strip_bogus_typing_prefix,
    _typing_registry_cache,
    _TypingEntry,
)


def _assert_pydantic_model_config_docstring() -> None:
    """Guard the upstream docstring the build assertions quote.

    ``pydantic.BaseModel.model_config``'s docstring is an *attribute*
    docstring: it lives in ``pydantic/main.py`` below the assignment, not
    on any object at runtime. Autodoc recovers it by parsing that module,
    so this guard uses the same mechanism (Sphinx's ``ModuleAnalyzer``)
    rather than plain introspection, which cannot see it.
    """
    analyzer = ModuleAnalyzer.for_module("pydantic.main")
    analyzer.analyze()
    lines = analyzer.attr_docs.get(("BaseModel", "model_config"))
    assert lines is not None, (
        "pydantic no longer defines an attribute docstring for "
        "BaseModel.model_config; the inherited-docstring assertions in "
        "test_autotypes_build need a new upstream fixture."
    )
    docstring = " ".join(lines)
    for expected in ("Configuration for the model", "ConfigDict"):
        assert expected in docstring, (
            f"pydantic reworded BaseModel.model_config's docstring "
            f"({expected!r} is gone): {docstring!r}. Update the HTML "
            "markers in test_autotypes_build to match."
        )


@pytest.mark.sphinx("html", testroot="autotypes")
def test_autotypes_build(app: SphinxTestApp, warning) -> None:
    """A nitpicky automodapi build over modern typing constructs is clean."""
    app.build()
    warnings = warning.getvalue()
    assert "reference target not found" not in warnings

    # The PEP 695 alias is documented as a py:type object with its
    # docstring recovered from the source below the type statement.
    objects = app.env.get_domain("py").objects
    assert "autotypespkg.StampValue" in objects
    assert objects["autotypespkg.StampValue"].objtype == "type"
    stamp_html = (
        app.outdir / "api" / "autotypespkg.StampValue.html"
    ).read_text()
    assert "A value that can be stamped into a registry." in stamp_html

    # The Annotated alias gets a stub (find_mod_objs patch) and shows the
    # docstring written below its assignment, not typing.Annotated's own.
    point_html = (
        app.outdir / "api" / "autotypespkg.SerializablePoint.html"
    ).read_text()
    assert "annotated for serialization" in point_html
    assert "Runtime representation of an annotated type" not in point_html

    # Alias references in annotations link to the alias's page.
    registry_html = (
        app.outdir / "api" / "autotypespkg.Registry.html"
    ).read_text()
    assert "autotypespkg.StampValue.html" in registry_html

    # References to importable external objects with no intersphinx
    # target (pydantic publishes no inventory) degrade to unlinked
    # literal text instead of warnings.
    assert "HttpUrl" in registry_html

    # A PEP 695 scoped type parameter that sphinx-autodoc-typehints
    # qualified with a bogus ``typing.`` prefix renders as unlinked
    # literal text (no <a> wrapper around the code span).
    stamper_html = (
        app.outdir / "api" / "autotypespkg.Stamper.html"
    ).read_text()
    marker = "typing.P"
    assert marker in stamper_html
    prefix = stamper_html[: stamper_html.index(marker)]
    code_start = prefix.rindex("<code")
    assert "<a" not in prefix[code_start - 120 : code_start]

    # A target carrying leaked ``repr()`` punctuation renders as unlinked
    # literal text (no <a> wrapper around the mangled code span).
    settings_html = (
        app.outdir / "api" / "autotypespkg.StampSettings.html"
    ).read_text()
    marker = "default_factory=&lt;lambda&gt;"
    assert marker in settings_html
    prefix = settings_html[: settings_html.index(marker)]
    code_start = prefix.rindex("<code")
    assert "<a" not in prefix[code_start - 120 : code_start]

    # A ``FieldInfo`` repr that *is* parseable Python is split into its
    # parts by the annotation parser, which emits a bare ``FieldInfo``
    # reference. It resolves only through the loaded modules of the
    # documented class's MRO package roots (``pydantic.fields``), and
    # degrades to unlinked literal text there.
    start = settings_html.index('id="autotypespkg.StampSettings.label"')
    label_sig = settings_html[start : settings_html.index("</dt>", start)]
    assert "FieldInfo" in label_sig
    # The only anchor in a fully degraded signature is the ¶ headerlink.
    assert label_sig.count("<a") == label_sig.count('<a class="headerlink"')

    # A bare name resolving to a class this project defines only under a
    # private module path (never re-exported, so no public documentation
    # target for it can exist) renders as unlinked literal text.
    marker = "StampScope</span></code>"
    assert marker in settings_html
    prefix = settings_html[: settings_html.index(marker)]
    code_start = prefix.rindex("<code")
    assert "<a" not in prefix[code_start - 120 : code_start]

    # A docstring inherited from an external base class (pydantic's
    # ``BaseModel.model_config``) references a bare ``ConfigDict``, a name
    # that only pydantic's own modules import. It resolves through the
    # documented class's MRO and degrades to unlinked literal text.
    #
    # The HTML markers below quote that upstream docstring, so guard on it
    # first: if pydantic rewords ``model_config``'s docstring, this fails
    # with an actionable message instead of a confusing marker mismatch.
    # This reads the same source autodoc does — the attribute docstring
    # parsed out of ``pydantic.main`` — via Sphinx's own module analyzer.
    _assert_pydantic_model_config_docstring()

    index_html = (app.outdir / "index.html").read_text()
    assert "Configuration for the model" in index_html
    marker = "ConfigDict</span></code>]"
    assert marker in index_html
    prefix = index_html[: index_html.index(marker)]
    code_start = prefix.rindex("<code")
    assert "<a" not in prefix[code_start - 120 : code_start]

    # Bare names that do resolve to project objects still link.
    assert "api/autotypespkg.Registry.html" in index_html


@pytest.mark.sphinx(
    "html",
    testroot="autotypes-inherited",
    srcdir="autotypes-inherited-linked",
)
def test_autotypes_inherited_docstring_links(
    app: SphinxTestApp, warning
) -> None:
    """A bare ref inherited from an external base links via intersphinx."""
    app.build()
    assert "reference target not found" not in warning.getvalue()

    # ``StampFormatter.write_local_file`` has no docstring of its own, so
    # the page carries the external base class's — including its bare
    # ``to_bytes`` reference, which names an attribute of that base rather
    # than anything in this package's namespace. The terminal name is
    # ambiguous in the stub inventory (``extpkg.Packer`` publishes a
    # ``to_bytes`` too), so only the name rebuilt from the MRO resolves.
    html = (app.outdir / "index.html").read_text()
    assert (
        "https://extpkg.example.com/formatter.html#extpkg.Formatter.to_bytes"
        in html
    )


@pytest.mark.sphinx(
    "html",
    testroot="autotypes-inherited",
    srcdir="autotypes-inherited-degraded",
    confoverrides={"intersphinx_mapping": {}},
)
def test_autotypes_inherited_docstring_degrades(
    app: SphinxTestApp, warning
) -> None:
    """The same ref degrades to an unlinked literal with no inventory."""
    app.build()
    assert "reference target not found" not in warning.getvalue()

    # Nothing can link the reference now, so it renders as literal text
    # rather than warning once per inherited docstring.
    html = (app.outdir / "index.html").read_text()
    assert "extpkg.example.com" not in html
    marker = ">to_bytes<"
    assert marker in html
    prefix = html[: html.index(marker)]
    code_start = prefix.rindex("<code")
    assert "<a" not in prefix[code_start - 120 : code_start]


@pytest.mark.sphinx("html", testroot="autotypes-private")
def test_autotypes_private_module_path(app: SphinxTestApp, warning) -> None:
    """A ref into this project's private module path degrades to text."""
    app.build()

    # The object is real but documented nowhere, so it renders as
    # unlinked literal text rather than as a nitpick warning.
    assert "privatepkg._impl.PrivateOnly" not in warning.getvalue()

    html = (app.outdir / "index.html").read_text()
    marker = "privatepkg._impl.PrivateOnly</span></code>"
    assert marker in html
    prefix = html[: html.index(marker)]
    code_start = prefix.rindex("<code")
    assert "<a" not in prefix[code_start - 120 : code_start]


@pytest.mark.sphinx(
    "html", testroot="autotypes-private", srcdir="autotypes-private-negatives"
)
def test_autotypes_private_module_path_negatives(
    app: SphinxTestApp, warning
) -> None:
    """Public-path and unimportable project references still warn."""
    app.build()
    warnings = warning.getvalue()

    # Project-local, but under a wholly public module path: this is the
    # "should be exported and documented but isn't" case, which the
    # private-segment gate deliberately leaves warning.
    assert (
        "reference target not found: privatepkg.helpers.PublicUndocumented"
        in warnings
    )

    # A typo under a private module path imports to nothing, so no rung
    # ever resolves an object for the degrade to reinterpret.
    assert (
        "reference target not found: privatepkg._impl.PrivateOnyl" in warnings
    )


@pytest.mark.sphinx(
    "html",
    testroot="autotypes-private",
    srcdir="autotypes-private-contextfree",
)
def test_autotypes_private_module_path_without_context(
    app: SphinxTestApp,
) -> None:
    """The context-free fully-qualified shape degrades the same way.

    Sphinx 9 reports some Pydantic annotation references from
    ``<unknown>:1``, with no ``refdoc``, ``py:module``, or ``py:class`` on
    the node at all. The dotted target imports on its own, so the rung can
    still reinterpret it — and its gate still applies.
    """
    app.build()

    def resolve(target: str) -> tuple[nodes.Element | None, nodes.Element]:
        contnode = nodes.literal("", target)
        node = addnodes.pending_xref(
            "", contnode, refdomain="py", reftype="obj", reftarget=target
        )
        return _missing_reference(app, app.env, node, contnode), contnode

    resolved, contnode = resolve("privatepkg._impl.PrivateOnly")
    assert resolved is contnode

    # Returning None is what leaves Sphinx to emit the nitpick warning.
    assert resolve("privatepkg.helpers.PublicUndocumented")[0] is None
    assert resolve("privatepkg._impl.PrivateOnyl")[0] is None


@pytest.mark.sphinx("html", testroot="autotypes-alias")
def test_autotypes_external_plain_alias(app: SphinxTestApp, warning) -> None:
    """A ref to an external plain-assignment alias degrades to text."""
    app.build()

    # The alias is a bare union object in a package that shares this
    # project's top-level root without being documented by it, so nothing
    # can ever link the reference: literal text, not a nitpick warning.
    assert "reference target not found: PathExpression" not in (
        warning.getvalue()
    )

    html = (app.outdir / "index.html").read_text()
    marker = "PathExpression</span></code>"
    assert marker in html
    prefix = html[: html.index(marker)]
    code_start = prefix.rindex("<code")
    assert "<a" not in prefix[code_start - 120 : code_start]


@pytest.mark.sphinx(
    "html", testroot="autotypes-alias", srcdir="autotypes-alias-negatives"
)
def test_autotypes_external_plain_alias_negatives(
    app: SphinxTestApp, warning
) -> None:
    """Project-local aliases and typo'd alias names still warn."""
    app.build()
    warnings = warning.getvalue()

    # A plain alias under one of this project's own documented module
    # prefixes is the "should be documented as a py:data/py:type object but
    # isn't" case, which the external gate deliberately leaves warning.
    assert "reference target not found: LocalAlias" in warnings

    # A typo names no alias in any scanned namespace, so no registry hit
    # exists for the degrade to act on.
    assert "reference target not found: PathExpresion" in warnings


@pytest.mark.sphinx(
    "html", testroot="autotypes-alias", srcdir="autotypes-alias-contextfree"
)
def test_autotypes_external_plain_alias_without_context(
    app: SphinxTestApp,
) -> None:
    """The context-free bare shape degrades the same way.

    Sphinx 9 reports the references that motivated this rung from
    ``<unknown>:1``, with no ``refdoc``, ``py:module``, or ``py:class`` on
    the node at all: nothing but the bare name is available, which is
    exactly what the registry is indexed by.
    """
    app.build()

    def resolve(target: str) -> tuple[nodes.Element | None, nodes.Element]:
        contnode = nodes.literal("", target)
        node = addnodes.pending_xref(
            "", contnode, refdomain="py", reftype="class", reftarget=target
        )
        return _missing_reference(app, app.env, node, contnode), contnode

    resolved, contnode = resolve("PathExpression")
    assert resolved is contnode

    # Returning None is what leaves Sphinx to emit the nitpick warning.
    assert resolve("LocalAlias")[0] is None
    assert resolve("PathExpresion")[0] is None


def _field_signature(html: str, object_id: str) -> str:
    """Return the signature markup of one documented object."""
    start = html.index(f'id="{object_id}"')
    return html[start : html.index("</dt>", start)]


@pytest.mark.sphinx("html", testroot="autotypes-annotated")
def test_autotypes_annotated_metadata(app: SphinxTestApp, warning) -> None:
    """Fragments of a field's Annotated metadata degrade to literal text."""
    app.build()
    assert "reference target not found" not in warning.getvalue()

    html = (app.outdir / "index.html").read_text()

    # The rendered types below are fully degraded, so the only anchor in
    # each signature is its own ¶ headerlink.
    def signature(field: str) -> str:
        sig = _field_signature(html, f"annotatedpkg.{field}")
        assert sig.count("<a") == sig.count('<a class="headerlink"')
        return sig

    # ``Ge``/``Le``: annotated_types constraint objects, reachable only
    # through the repr of the field's ``FieldInfo``.
    rate = signature("SentryConfig.traces_sample_rate")
    assert ">Ge<" in rate
    assert ">Le<" in rate

    # ``file``: a dataclass metadata field's string value, stringified
    # into the rendered type without its quotes.
    assert ">file<" in signature("KafkaSettings.cluster_ca_path")

    # Enum members named by attribute path in a source-text annotation.
    phase = signature("Job.phase")
    for member in ("PENDING", "EXECUTING", "COMPLETED"):
        assert f">ExecutionPhase.{member}<" in phase


@pytest.mark.sphinx(
    "html", testroot="autotypes-annotated", srcdir="autotypes-annotated-neg"
)
def test_autotypes_annotated_metadata_negatives(app: SphinxTestApp) -> None:
    """Names no metadata rendering produces keep warning."""
    app.build()

    def resolve(target: str, klass: str) -> nodes.Element | None:
        contnode = nodes.literal("", target)
        node = addnodes.pending_xref(
            "",
            contnode,
            refdomain="py",
            reftype="class",
            reftarget=target,
            **{"py:module": "annotatedpkg", "py:class": klass},
        )
        return _missing_reference(app, app.env, node, contnode)

    # The fragments themselves degrade, on the class whose metadata
    # produces them.
    assert resolve("Ge", "SentryConfig") is not None
    assert resolve("file", "KafkaSettings") is not None
    assert resolve("ExecutionPhase.PENDING", "Job") is not None

    # A typo of a fragment is in no rendering, so it still warns.
    assert resolve("Gee", "SentryConfig") is None
    assert resolve("ExecutionPhase.PENDNIG", "Job") is None

    # So does a never-importable dotted name.
    assert resolve("annotatedpkg.nosuchmodule.Thing", "SentryConfig") is None

    # The index is per class: a fragment of one model's metadata does not
    # degrade the same name on another model's page.
    assert resolve("Ge", "Job") is None
    assert resolve("ExecutionPhase.PENDING", "SentryConfig") is None


@pytest.mark.sphinx("html", testroot="autotypes-typehints")
def test_autotypes_callable_singleton(app: SphinxTestApp, warning) -> None:
    """A module-level callable singleton survives the build."""
    app.build()

    # Sphinx 9 allocates ``data`` objects no signature slot, while
    # sphinx-autodoc-typehints returns a signature tuple for any annotated
    # callable — including this one. Sphinx then indexes into the empty
    # signature list, and the resulting IndexError is swallowed as a
    # warning that silently drops the object from the built docs.
    assert "error while formatting signature" not in warning.getvalue()

    # The singleton is documented (with no signature line, matching
    # Sphinx 9's own model for data objects).
    html = (app.outdir / "index.html").read_text()
    assert 'id="singletonpkg.auth_dependency"' in html
    assert "The process-wide dependency instance." in html


@pytest.mark.sphinx("html", testroot="autotypes-pydantic")
def test_autotypes_pydantic_model_members(app: SphinxTestApp) -> None:
    """Non-field members stay on an autodoc-pydantic model page."""
    app.build()

    # autodoc-pydantic's model documenter uses autodoc's legacy
    # class-based API, whose member dispatch looks candidate documenters
    # up in the registry. Sphinx 9 populates that registry with its own
    # built-in documenters only under ``autodoc_use_legacy_class_based``,
    # so without the compat shim an ordinary method, classmethod, or
    # property has no documenter and is dropped from the page.
    html = (app.outdir / "index.html").read_text()
    for member in ("serialize", "deserialize", "shout"):
        assert f'id="pydanticpkg.StampConfig.{member}"' in html

    # The field the model documenter does handle keeps its own rendering.
    assert 'id="pydanticpkg.StampConfig.label"' in html

    # Prose references to a restored member resolve to it.
    assert "#pydanticpkg.StampConfig.deserialize" in html


def test_restore_legacy_member_documenters() -> None:
    """The registry fill never displaces another extension's documenter."""

    class ThirdPartyDocumenter:
        objtype = "class"

    class Registry:
        def __init__(self) -> None:
            self.documenters = {"class": ThirdPartyDocumenter}

    class App:
        def __init__(self) -> None:
            self.registry = Registry()

    app = App()
    _restore_legacy_member_documenters(app)

    # The object types autodoc-pydantic model pages lose on Sphinx 9 now
    # have a documenter able to claim them.
    for objtype in ("method", "property", "attribute", "data"):
        assert app.registry.documenters[objtype].objtype == objtype

    # An extension that registered its own documenter for a built-in
    # object type keeps it, whichever order the two setups ran in.
    assert app.registry.documenters["class"] is ThirdPartyDocumenter


def test_suppress_data_signature() -> None:
    """Only data and attribute objects short-circuit the signature event."""
    # ``emit_firstresult`` stops at the first non-``None`` result, so the
    # two-``None`` tuple is what keeps a later handler from supplying a
    # signature — and Sphinx's ``isinstance(result[0], str)`` guard then
    # skips the assignment that would raise ``IndexError``.
    for what in ("data", "attribute"):
        assert _suppress_data_signature(
            None, what, "pkg.thing", object(), None, None, None
        ) == (None, None)

    # Everything else falls through to the handlers that do compute
    # signatures, so annotated callables keep theirs.
    for what in ("module", "class", "method", "function", "property"):
        assert (
            _suppress_data_signature(
                None, what, "pkg.thing", object(), None, None, None
            )
            is None
        )


@pytest.mark.parametrize(
    "extension",
    [
        "documenteer.ext.autotypes",
        "documenteer.ext.autotypes.documenters",
        "documenteer.ext.autotypes.compat",
        "documenteer.ext.autotypes.xrefs",
    ],
)
def test_subextensions_are_individually_loadable(
    make_app, tmp_path, extension
) -> None:
    """Each sub-extension sets up on its own, and the umbrella once."""
    srcdir = tmp_path / extension.rsplit(".", 1)[-1]
    srcdir.mkdir()
    (srcdir / "conf.py").write_text(f'extensions = ["{extension}"]\n')
    (srcdir / "index.rst").write_text("Title\n=====\n")
    app = make_app(srcdir=srcdir)
    app.build()
    assert app.statuscode == 0
    assert app.warning.getvalue() == ""


def test_lookup_runtime_object_class_mro(rootdir) -> None:
    """Bare names resolve through the documented class's MRO."""
    import sys  # noqa: PLC0415

    sys.path.insert(0, str(rootdir / "test-autotypes"))
    try:
        import autotypespkg  # noqa: PLC0415
        from pydantic import ConfigDict  # noqa: PLC0415

        # ``ConfigDict`` is not importable from the documented package,
        # so the page's ``py:module`` namespace cannot resolve it.
        assert _lookup_runtime_object("ConfigDict", "autotypespkg") is None

        # It is importable from ``pydantic.main``, the module that defines
        # the base class whose docstring the reference came from.
        assert (
            _lookup_runtime_object(
                "ConfigDict", "autotypespkg", "StampSettings"
            )
            is ConfigDict
        )

        # Project-local names keep resolving from the module namespace.
        assert (
            _lookup_runtime_object("Registry", "autotypespkg", "StampSettings")
            is autotypespkg.Registry
        )

        # Genuine typos resolve to nothing, so they still warn.
        assert (
            _lookup_runtime_object(
                "ConfigDcit", "autotypespkg", "StampSettings"
            )
            is None
        )

        # A class context that names nothing importable is ignored.
        assert (
            _lookup_runtime_object("ConfigDict", "autotypespkg", "Nonesuch")
            is None
        )

        # Every MRO ends at ``object``, so ``builtins`` is skipped: a bare
        # name colliding with a builtin must keep warning rather than
        # silently resolving on any class page.
        for builtin_name in ("input", "min", "dict"):
            assert (
                _lookup_runtime_object(
                    builtin_name, "autotypespkg", "StampSettings"
                )
                is None
            )
    finally:
        sys.path.pop(0)


def test_lookup_runtime_object_mro_root_packages(rootdir) -> None:
    """Bare names resolve through the MRO's top-level packages."""
    import sys  # noqa: PLC0415

    sys.path.insert(0, str(rootdir / "test-autotypes"))
    try:
        import pydantic  # noqa: PLC0415
        import pydantic.main  # noqa: PLC0415
        from pydantic.fields import FieldInfo  # noqa: PLC0415

        # ``FieldInfo`` is exposed by neither the documented package, nor
        # ``pydantic`` itself, nor ``pydantic.main`` (the module defining
        # the MRO class whose docstrings the page inherits), so every
        # earlier rung misses it.
        assert not hasattr(pydantic, "FieldInfo")
        assert not hasattr(pydantic.main, "FieldInfo")
        assert _lookup_runtime_object("FieldInfo", "autotypespkg") is None

        # ``pydantic.fields`` is under the MRO's ``pydantic`` root, so the
        # scan of loaded modules finds it.
        assert (
            _lookup_runtime_object(
                "FieldInfo", "autotypespkg", "StampSettings"
            )
            is FieldInfo
        )
    finally:
        sys.path.pop(0)


def test_lookup_runtime_object_mro_root_packages_misses(rootdir) -> None:
    """Names in no MRO-root package stay unresolved, so typos still warn."""
    import sys  # noqa: PLC0415

    sys.path.insert(0, str(rootdir / "test-autotypes"))
    try:
        # A typo of a name the rung *can* resolve.
        assert (
            _lookup_runtime_object(
                "FeildInfo", "autotypespkg", "StampSettings"
            )
            is None
        )
        # A real class (imported at the top of this module, so it is in
        # ``sys.modules``) belonging to a package that is in none of the
        # MRO's roots.
        assert ModuleAnalyzer is not None
        assert (
            _lookup_runtime_object(
                "ModuleAnalyzer", "autotypespkg", "StampSettings"
            )
            is None
        )
    finally:
        sys.path.pop(0)


def test_lookup_mro_attribute(rootdir) -> None:
    """A bare name found as an MRO class's attribute reports its full name."""
    import sys  # noqa: PLC0415

    sys.path.insert(0, str(rootdir / "test-autotypes-inherited"))
    try:
        import extpkg  # noqa: PLC0415
        import inheritpkg  # noqa: PLC0415

        # ``to_bytes`` is an attribute of an external base class, not a
        # name in any MRO class's defining-module namespace.
        found = _lookup_mro_attribute("to_bytes", inheritpkg.StampFormatter)
        assert found is not None
        obj, fqn = found
        assert obj is extpkg.Formatter.to_bytes
        # The name is rebuilt from the class that *defines* the attribute,
        # not from the class the reference was rendered inside.
        assert fqn == "extpkg.Formatter.to_bytes"

        # An override is attributed to the overriding class.
        found = _lookup_mro_attribute(
            "write_local_file", inheritpkg.StampFormatter
        )
        assert found is not None
        assert found[1] == "inheritpkg.StampFormatter.write_local_file"

        # Genuine typos are defined by no class in the MRO, so they stay
        # unresolved and keep warning.
        assert (
            _lookup_mro_attribute("to_btyes", inheritpkg.StampFormatter)
            is None
        )
    finally:
        sys.path.pop(0)


def test_lookup_runtime_object_mro_attribute(rootdir) -> None:
    """Bare names resolve to attributes inherited from an external base."""
    import sys  # noqa: PLC0415

    sys.path.insert(0, str(rootdir / "test-autotypes-inherited"))
    try:
        import extpkg  # noqa: PLC0415

        # Without the class the reference was rendered inside, an
        # inherited attribute name is unreachable: it is a member of no
        # module namespace.
        assert _lookup_runtime_object("to_bytes", "inheritpkg") is None

        # With it, the MRO's attributes are searched, so the reference can
        # reach the external-object degrade path.
        assert (
            _lookup_runtime_object("to_bytes", "inheritpkg", "StampFormatter")
            is extpkg.Formatter.to_bytes
        )
    finally:
        sys.path.pop(0)


def test_lookup_mro_attribute_skips_builtins() -> None:
    """Builtin base classes, and builtin names, never resolve here."""

    class Mapping(dict):
        """A class whose MRO reaches a builtin type other than object."""

    assert "get" not in vars(Mapping)
    assert _lookup_mro_attribute("get", Mapping) is None

    class Model:
        """A class defining methods that collide with builtin names."""

        def dict(self) -> None:
            """Stand in for ``pydantic.BaseModel.dict``."""

        def to_bytes(self) -> None:
            """Stand in for a method whose name collides with nothing."""

    # A bare ``dict`` in a docstring means the builtin type, so it keeps
    # warning rather than resolving to a same-named method.
    assert _lookup_mro_attribute("dict", Model) is None
    assert _lookup_mro_attribute("to_bytes", Model) is not None


def test_mro_root_namespace_ambiguity(monkeypatch) -> None:
    """A name meaning different objects in different modules is unresolved."""
    import sys  # noqa: PLC0415
    import types  # noqa: PLC0415

    shared = object()
    pkg = types.ModuleType("_autotypes_probe")
    one = types.ModuleType("_autotypes_probe.one")
    two = types.ModuleType("_autotypes_probe.two")
    one.Agreed = shared
    two.Agreed = shared
    one.Disputed = object()
    two.Disputed = object()
    for name, module in (
        ("_autotypes_probe", pkg),
        ("_autotypes_probe.one", one),
        ("_autotypes_probe.two", two),
    ):
        monkeypatch.setitem(sys.modules, name, module)

    index = _mro_root_namespace(frozenset({"_autotypes_probe"}))
    assert index["Agreed"] is shared
    assert index["Disputed"] is _AMBIGUOUS


class _StubEnv:
    """Stand-in for the parts of the build environment the ladder reads.

    ``_is_project_private_runtime_object`` only needs the set of module
    names the project documents, which is exactly what the predicate it
    shares its project-local test with (``_is_external_runtime_object``)
    reads out of the Python domain's data.
    """

    def __init__(self, *modules: str) -> None:
        self.domaindata = {"py": {"modules": dict.fromkeys(modules)}}


def _object_defined_in(modname: str) -> type:
    """Build a class that reports *modname* as its defining module."""

    class Probe:
        """A stand-in for an object the reference ladder resolved."""

    Probe.__module__ = modname
    return Probe


def test_is_project_private_runtime_object() -> None:
    """Only project-local objects under private module paths degrade."""
    env = _StubEnv("privatepkg", "otherpkg.public")

    # Project-local and defined under a private module path: no public
    # documentation target for it can ever exist.
    assert _is_project_private_runtime_object(
        env, _object_defined_in("privatepkg._impl")
    )
    # The private segment can be anywhere in the path, at any depth.
    assert _is_project_private_runtime_object(
        env, _object_defined_in("privatepkg._transforms._transform")
    )
    assert _is_project_private_runtime_object(
        env, _object_defined_in("privatepkg.serialization._migrations")
    )

    # Project-local but wholly public: something that should be exported
    # and documented but isn't, so the reference keeps warning.
    assert not _is_project_private_runtime_object(
        env, _object_defined_in("privatepkg")
    )
    assert not _is_project_private_runtime_object(
        env, _object_defined_in("privatepkg.helpers")
    )

    # External objects are the external-object rung's business, whether
    # or not their own module paths are private.
    assert not _is_project_private_runtime_object(
        env, _object_defined_in("pydantic.fields")
    )
    assert not _is_project_private_runtime_object(
        env, _object_defined_in("pydantic._internal._model_construction")
    )
    # A documented module name is a prefix only at a path boundary.
    assert not _is_project_private_runtime_object(
        env, _object_defined_in("privatepkgx._impl")
    )

    # Objects with no defining module at all are left to warn.
    assert not _is_project_private_runtime_object(env, object())


def test_is_plain_type_alias() -> None:
    """Only plain-assignment union aliases are classified as such."""
    import types  # noqa: PLC0415
    from pathlib import Path  # noqa: PLC0415
    from typing import Annotated, Optional, TypeVar, Union  # noqa: PLC0415

    # Both spellings of a union alias, on every supported Python: 3.14
    # makes ``X | Y`` a ``typing.Union`` while earlier versions make it a
    # ``types.UnionType``, and ``Union[...]`` is the mirror image.
    assert _is_plain_type_alias(str | Path)
    assert _is_plain_type_alias(Union[str, Path])  # noqa: UP007
    assert _is_plain_type_alias(Optional[str])  # noqa: UP045
    assert _is_plain_type_alias(str | None)

    # Ordinary types, values, and the other alias kinds the registry
    # already classifies on their own are not plain aliases.
    assert not _is_plain_type_alias(int)
    assert not _is_plain_type_alias(Path)
    assert not _is_plain_type_alias("a string")
    assert not _is_plain_type_alias(TypeVar("T"))
    assert not _is_plain_type_alias(Annotated[int, "marker"])

    # Other subscripted generics are left alone: a union is the form a
    # plain-assignment alias takes, and widening past it would admit
    # values that are not aliases at all.
    assert not _is_plain_type_alias(list[int])
    assert not _is_plain_type_alias(dict[str, int])
    assert not _is_plain_type_alias(types.SimpleNamespace())


@pytest.fixture
def clear_typing_registry_cache():
    """Isolate the project typing registry's single-entry cache.

    The cache is keyed by ``id(env)`` and holds one entry, so a stub
    environment's registry could otherwise be served to (or from) another
    test whose environment object happens to land on the same address.
    """
    _typing_registry_cache.clear()
    yield
    _typing_registry_cache.clear()


def _install_modules(
    monkeypatch, modules: dict[str, dict[str, object]]
) -> None:
    """Register synthetic modules in ``sys.modules`` for one test.

    The typing registry scans the already-imported modules under the
    documented modules' top-level roots, so a package tree in
    ``sys.modules`` is the whole input it reads.
    """
    import sys  # noqa: PLC0415
    import types  # noqa: PLC0415

    for name, attrs in modules.items():
        module = types.ModuleType(name)
        for attr, value in attrs.items():
            setattr(module, attr, value)
        monkeypatch.setitem(sys.modules, name, module)


def test_project_typing_registry_records_plain_aliases(
    monkeypatch, clear_typing_registry_cache
) -> None:
    """Plain union aliases are recorded with the module they were found in."""
    from pathlib import Path  # noqa: PLC0415

    alias = str | Path
    _install_modules(
        monkeypatch,
        {
            "aliasprobe": {},
            "aliasprobe.documented": {"Loader": type("Loader", (), {})},
            "aliasprobe.external": {"PathExpression": alias},
        },
    )

    registry = _project_typing_registry(_StubEnv("aliasprobe.documented"))

    # A union object knows neither its name nor its defining module, so the
    # module it was found in is recorded alongside it.
    assert [(e.value, e.module) for e in registry["PathExpression"]] == [
        (alias, "aliasprobe.external")
    ]

    # Ordinary module attributes are still not registry entries.
    assert "Loader" not in registry


def test_project_typing_registry_keeps_typevar_entries(
    monkeypatch, clear_typing_registry_cache
) -> None:
    """TypeVars and PEP 695 aliases keep being recorded, with provenance."""
    from typing import TypeAliasType, TypeVar  # noqa: PLC0415

    T = TypeVar("T")
    alias = TypeAliasType("StampValue", int | str)
    _install_modules(
        monkeypatch,
        {
            "varprobe": {},
            "varprobe.documented": {"T": T, "StampValue": alias},
        },
    )

    registry = _project_typing_registry(_StubEnv("varprobe.documented"))

    assert [(e.value, e.module) for e in registry["T"]] == [
        (T, "varprobe.documented")
    ]
    assert [e.value for e in registry["StampValue"]] == [alias]


def _entries(*pairs: tuple[object, str]) -> list[_TypingEntry]:
    """Build registry entries from ``(value, module)`` pairs."""
    return [_TypingEntry(value, module) for value, module in pairs]


def test_is_unlinkable_registry_match_plain_aliases() -> None:
    """A plain alias degrades only when every hit is external."""
    from pathlib import Path  # noqa: PLC0415

    env = _StubEnv("aliasprobe.documented")
    alias = str | Path

    # Found only in a sibling package that shares this project's top-level
    # root without being under any documented module prefix: no target for
    # it can exist here, so the reference degrades.
    assert _is_unlinkable_registry_match(
        env, _entries((alias, "aliasprobe.external"))
    )

    # The same object re-exported from a second external module is still
    # one object, so the identical-object rule holds.
    assert _is_unlinkable_registry_match(
        env,
        _entries(
            (alias, "aliasprobe.external"),
            (alias, "aliasprobe.external._impl"),
        ),
    )

    # Under a documented module prefix — public or private path — the alias
    # is this project's own to document as ``py:data``/``py:type``, so the
    # reference keeps warning.
    assert not _is_unlinkable_registry_match(
        env, _entries((alias, "aliasprobe.documented"))
    )
    assert not _is_unlinkable_registry_match(
        env, _entries((alias, "aliasprobe.documented.helpers"))
    )

    # One project-local hit is enough to keep the name warning.
    assert not _is_unlinkable_registry_match(
        env,
        _entries(
            (alias, "aliasprobe.external"),
            (alias, "aliasprobe.documented.helpers"),
        ),
    )

    # Two *different* union objects under one name cannot be resolved to
    # either of them, so the ambiguity rule keeps the reference warning.
    assert not _is_unlinkable_registry_match(
        env,
        _entries(
            (alias, "aliasprobe.external"),
            (str | int, "aliasprobe.other"),
        ),
    )

    # A name with no registry hits at all (a typo) never degrades here.
    assert not _is_unlinkable_registry_match(env, [])


def test_is_unlinkable_registry_match_typing_objects() -> None:
    """Objects unlinkable in themselves degrade wherever they were found."""
    from typing import Annotated, TypeAliasType, TypeVar  # noqa: PLC0415

    env = _StubEnv("aliasprobe.documented")

    # TypeVars, PEP 695 aliases, and Annotated aliases have no target of
    # their own, so their provenance never enters into it — including in
    # the project's own modules, which is the pre-existing behavior.
    for value in (
        TypeVar("T"),
        TypeAliasType("StampValue", int | str),
        Annotated[int, "marker"],
    ):
        assert _is_unlinkable_registry_match(
            env, _entries((value, "aliasprobe.documented"))
        )

    # A name that is a TypeVar in one module and an external plain alias in
    # another is unlinkable either way, so it still degrades.
    assert _is_unlinkable_registry_match(
        env,
        _entries(
            (TypeVar("T"), "aliasprobe.documented"),
            (int | str, "aliasprobe.external"),
        ),
    )


def test_candidate_names() -> None:
    assert _candidate_names("pkg._private.Thing") == [
        "pkg._private.Thing",
        "pkg.Thing",
    ]
    assert _candidate_names("Thing") == []


def test_is_mangled_target() -> None:
    # repr() leakage from Annotated field metadata.
    assert _is_mangled_target(
        "FieldInfo(annotation=NoneType, required=False, "
        "default_factory=<lambda>)"
    )
    assert _is_mangled_target(
        "lambda>)]) <safir.metrics._config.DisabledMetricsConfig.enabled"
    )
    assert _is_mangled_target("ExecutionPhase.PENDING: 'PENDING'>, ...])])")
    assert _is_mangled_target(
        "typing.Annotated[bool, FieldInfo(default_factory=<lambda>)]"
    )

    # Dotted-name mistakes (typo'd module paths) are still warnable.
    assert not _is_mangled_target("pkg.subpkg.Thnig")
    assert not _is_mangled_target("Thing")
    assert not _is_mangled_target("pkg._impl.Thing")

    # Parameterized references keep resolving by their base name.
    assert not _is_mangled_target("Model[Any]")
    assert not _is_mangled_target("dict[str, StampValue]")


def _annotated_class(**annotations: object) -> type:
    """Build a class whose ``__annotations__`` are exactly *annotations*.

    Sphinx renders a member's type from the annotation values it finds on
    the class, so setting them directly is what pins each rendering path
    under test: real ``Annotated`` objects for the evaluated case, and a
    string for the unevaluated :pep:`563` case. (This test module itself
    uses ``from __future__ import annotations``, so a class written with
    ordinary annotation syntax here could only exercise the second.)
    """

    class Probe:
        """A stand-in for a documented class."""

    Probe.__annotations__ = dict(annotations)
    return Probe


def test_annotated_metadata_fragments_runtime() -> None:
    """Constraint objects nested in a rendered ``FieldInfo`` are fragments."""
    from typing import Annotated  # noqa: PLC0415

    from pydantic import Field  # noqa: PLC0415

    cls = _annotated_class(rate=Annotated[float, Field(ge=0, le=1)])
    fragments = _annotated_metadata_fragments(cls)

    # ``Ge`` and ``Le`` only ever appear inside the ``FieldInfo`` repr that
    # Sphinx unparses; they are in no module namespace the ladder scans.
    assert {"FieldInfo", "Ge", "Le"} <= fragments

    # The annotated *type* is not metadata, so it keeps following the
    # ordinary ladder rather than degrading here.
    assert "float" not in fragments


def test_annotated_metadata_fragments_dataclass_value() -> None:
    """A dataclass metadata field's *value* is a fragment too."""
    from pathlib import Path  # noqa: PLC0415
    from typing import Annotated  # noqa: PLC0415

    from pydantic.types import PathType  # noqa: PLC0415

    cls = _annotated_class(
        ca_path=Annotated[Path, PathType("file")] | None,
    )
    fragments = _annotated_metadata_fragments(cls)

    # Sphinx renders dataclass metadata by stringifying each field value,
    # which drops the quotes from the string ``"file"`` and leaves a bare
    # name behind that names no object at all.
    assert "file" in fragments
    assert "pydantic.types.PathType" in fragments

    # The metadata of a *nested* ``Annotated`` counts, but the annotated
    # type itself still does not.
    assert "Path" not in fragments
    assert "pathlib.Path" not in fragments


def test_annotated_metadata_fragments_source_text() -> None:
    """Fragments are found in unevaluated source-text annotations as well."""
    cls = _annotated_class(
        phase="Annotated[Phase, Field(examples=[Phase.DRAFT, Phase.FINAL])]",
    )
    fragments = _annotated_metadata_fragments(cls)

    # Enum members used as metadata arguments unparse to dotted targets.
    assert {"Field", "Phase.DRAFT", "Phase.FINAL"} <= fragments

    # Only the metadata positions count: the annotated type itself keeps
    # following the ordinary ladder.
    assert "Phase" not in fragments


def test_annotated_metadata_fragments_misses() -> None:
    """Names no metadata expression renders are not fragments."""
    from typing import Annotated  # noqa: PLC0415

    from pydantic import Field  # noqa: PLC0415

    fragments = _annotated_metadata_fragments(
        _annotated_class(rate=Annotated[float, Field(ge=0, le=1)])
    )

    # A typo of a name the rung *does* cover keeps warning.
    assert "Gee" not in fragments
    # So does a real but unrelated class.
    assert "ModuleAnalyzer" not in fragments

    # An annotation that carries no metadata at all contributes nothing,
    # and neither does an unparseable one.
    assert _annotated_metadata_fragments(_annotated_class()) == frozenset()
    assert (
        _annotated_metadata_fragments(_annotated_class(rate=float))
        == frozenset()
    )
    assert (
        _annotated_metadata_fragments(
            _annotated_class(rate="Annotated[float, Field(<lambda>)]")
        )
        == frozenset()
    )


def test_strip_bogus_typing_prefix() -> None:
    # PEP 695 scoped type parameters that sphinx-autodoc-typehints
    # qualified with a bogus ``typing.`` prefix.
    assert _strip_bogus_typing_prefix("typing.P") == "P"
    assert _strip_bogus_typing_prefix("typing.EventPayload") == "EventPayload"

    # Genuine typing members are attributes of the module and keep their
    # fully-qualified target so intersphinx resolution is untouched.
    assert _strip_bogus_typing_prefix("typing.Union") == "typing.Union"
    assert _strip_bogus_typing_prefix("typing.Annotated") == "typing.Annotated"
    assert _strip_bogus_typing_prefix("typing.TypeVar") == "typing.TypeVar"

    # Only a single-segment name under ``typing`` is a candidate; other
    # targets pass through unchanged.
    assert _strip_bogus_typing_prefix("pkg.P") == "pkg.P"
    assert _strip_bogus_typing_prefix("typing") == "typing"
    assert _strip_bogus_typing_prefix("typing.io.TextIO") == "typing.io.TextIO"
    assert _strip_bogus_typing_prefix("P") == "P"


def test_is_annotated_alias() -> None:
    from typing import Annotated  # noqa: PLC0415

    assert _is_annotated_alias(Annotated[int, "marker"])
    assert not _is_annotated_alias(int)
    assert not _is_annotated_alias("a string")


def test_find_alias_docstring(rootdir) -> None:
    import sys  # noqa: PLC0415

    sys.path.insert(0, str(rootdir / "test-autotypes"))
    try:
        from autotypespkg import _impl  # noqa: PLC0415

        assert (
            _find_alias_docstring(_impl.StampValue)
            == "A value that can be stamped into a registry."
        )
        assert (
            _find_assignment_docstring(
                "autotypespkg._impl", "SerializablePoint"
            )
            == "A `Point` annotated for serialization."
        )
        assert _find_assignment_docstring("autotypespkg._impl", "nope") is None
    finally:
        sys.path.pop(0)
