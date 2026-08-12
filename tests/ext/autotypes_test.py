# type: ignore
"""Tests for documenteer.ext.autotypes."""

from __future__ import annotations

import pytest
from sphinx.pycode import ModuleAnalyzer
from sphinx.testing.util import SphinxTestApp

from documenteer.ext.autotypes._shared import _is_annotated_alias
from documenteer.ext.autotypes.documenters import (
    _find_alias_docstring,
    _find_assignment_docstring,
)
from documenteer.ext.autotypes.xrefs import (
    _AMBIGUOUS,
    _candidate_names,
    _is_mangled_target,
    _lookup_runtime_object,
    _mro_root_namespace,
    _strip_bogus_typing_prefix,
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
