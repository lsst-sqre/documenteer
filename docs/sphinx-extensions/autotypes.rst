.. _documenteer-ext-autotypes:

################################
Python type aliases and TypeVars
################################

Documenteer's ``documenteer.ext.autotypes`` extension bridges gaps in the autodoc_/automodapi_/autodoc-pydantic_ ecosystem for Python APIs that use modern typing constructs, like :pep:`695` ``type`` aliases, ``Annotated`` aliases, and type variables.
Without it, projects like these accumulate long ``nitpick_ignore`` lists for references that Sphinx cannot resolve, and type-alias pages render with the docstring of :class:`typing.TypeAliasType` itself instead of anything useful.

.. tip::

   If you use Documenteer's user-guide configuration preset, this extension is already enabled.
   To use it elsewhere, add ``"documenteer.ext.autotypes"`` to the ``extensions`` list in your :file:`conf.py`.

Features
========

Documenting type aliases
------------------------

A module-level ``type`` statement (:pep:`695`) is documented as a ``py:type`` object using the docstring written below the statement:

.. code-block:: python

   type MetadataValue = int | float | str | bool | None
   """A value that can be stored in image metadata."""

On Sphinx 8, the extension backports the ``autotype`` documenter (the ``py:type`` directive itself exists since Sphinx 8.2); on Sphinx 9, which documents aliases natively, it adds the docstring support that Sphinx does not yet have.
Because the documenter is registered with autodoc, sphinx-automodapi_ generates ``autotype`` stub pages automatically.

Documenting ``Annotated`` aliases
---------------------------------

A pre-:pep:`695`, assignment-style alias such as ``SerializablePoint = Annotated[Point, ...]`` binds the name to the bare ``Annotated[...]`` object, which carries *typing's* identity rather than its own: ``__module__ == "typing"`` and ``__name__ == "Annotated"``.
(A ``type`` statement instead creates a :class:`typing.TypeAliasType` that knows its defining module and name, which is why the two forms need separate handling.)
That identity mismatch makes sphinx-automodapi_ list the alias in summary tables while excluding it from stub generation ("stub file not found" warnings), and makes autodoc render :class:`typing.Annotated`'s own docstring.
The extension fixes both: the alias's fully-qualified name is derived from the module documenting it, and its docstring is recovered from the source below its assignment — even when the alias is documented from a public re-export location rather than its defining module.
(Python binds a below-statement docstring to ``__doc__`` for neither alias form, so both go through the same AST-based docstring recovery.)

Restoring autodoc-pydantic under Sphinx 9
-----------------------------------------

Sphinx 9's autodoc rewrite removed the registry-based API that sphinx-automodapi_ used to classify objects, so Pydantic models degrade from ``autopydantic_model`` stubs to generic ``autoclass`` stubs that document every inherited ``BaseModel`` member — producing thousands of nitpick warnings sourced from Pydantic's own docstrings.
The extension patches automodapi_\ ’s object classification to consult third-party autodoc documenters again.\ [#click]_

Sphinx 9 also drops every *non-field* member — ordinary methods, classmethods, properties, and attributes — from ``autopydantic_model`` pages, so a model's real API disappears and prose references to it (``ArchiveTree.deserialize``) warn.
autodoc-pydantic_ documents members through autodoc's legacy class-based API, which chooses a documenter for each member from the ones registered with autodoc and skips the member when none can claim it.
Sphinx 9 registers its own built-in documenters there only under ``autodoc_use_legacy_class_based``, leaving autodoc-pydantic_\ ’s own field, validator, and config documenters as the entire candidate pool.
The extension registers the built-in documenters again, which restores those members without switching the build over to the legacy API: ``autoclass``, ``automethod``, and the rest keep dispatching to Sphinx 9's native implementation.
Projects that pinned ``sphinx<9`` in their documentation requirements because of this can lift the pin.

.. [#click] It also repairs sphinx-click's ``mock`` import, which can break under Sphinx 9 with ``TypeError: 'module' object is not callable`` when another extension imports ``sphinx.ext.autodoc.mock``.

Keeping callable singletons in the build
----------------------------------------

A module-level instance of a ``__call__``-defining class — the shape Safir's ``*_dependency`` injection helpers use — disappears from Sphinx 9 builds that also run sphinx-autodoc-typehints_, with only an ``error while formatting signature ... [autodoc]`` warning to show for it.
Sphinx 9 gives ``data`` objects no signature slot, while sphinx-autodoc-typehints_ computes a signature for *any* annotated callable, and Sphinx then assigns that signature into an empty list.
The extension answers the ``autodoc-process-signature`` event ahead of sphinx-autodoc-typehints_ for ``data`` and ``attribute`` objects, so nothing supplies a signature Sphinx has nowhere to put and the object documents without a signature line — which is how Sphinx 9 renders data objects anyway.

Resolving cross-references
--------------------------

Autodoc_, sphinx-autodoc-typehints_, napoleon, and autodoc-pydantic_ emit references under names that might not match a documented target exactly.
A ``missing-reference`` handler resolves, in order:

#. **Bogus** ``typing.`` **prefixes** on :pep:`695` scoped type parameters, before any resolution is attempted: sphinx-autodoc-typehints_ qualifies the ``P`` of ``class C[P: Base]`` as ``typing.P``, which no member of the module matches. A single-segment ``typing.<name>`` target that is not an attribute of the typing module is reduced to the bare name and re-run through the bare-name rungs below; genuine members such as :class:`typing.Union` keep their fully-qualified target and their intersphinx resolution.
#. **Role mismatches**, locally and against intersphinx inventories: a ``py:data`` reference to :class:`typing.Union`, or a ``py:class`` reference to a ``py:type`` alias target.
#. **Private-path references** for objects re-exported from a public package: ``lsst.images._geom.XY`` resolves to the documented ``lsst.images.XY``, and ``h5py._hl.files.File`` to the public ``h5py.File`` in the h5py inventory.
#. **Bare names** from field annotations and docstrings (``Registry``), by unambiguous suffix match over this project's own documented objects, and then over intersphinx inventories\ [#suffix]_.
#. **Class- and module-relative references** (``ArchiveTree.deserialize``, ``cameras.Orientation.to_legacy``) by resolving the head and looking up the rest beneath it.
#. **Modules documented with** ``automodapi`` **and** ``:no-main-docstr:``, which otherwise have no ``py:module`` target at all; references to them link to the automodapi page.
#. **Parameterized references** (``Model[Any]``) by their base name.

.. [#suffix] Suffix matching is deliberately conservative:

   - Bare names match only when exactly one documented object (or one intersphinx entry across all inventories) has that terminal name.
   - Dotted names are only re-anchored along their own module path, or matched by terminal name when they already start with one of this project's documented module prefixes.
     An external reference like ``lsst.afw.image.Mask`` is never linked to an unrelated local ``Mask``.

Before any of that, targets that could never be dotted Python names in the first place are degraded to unlinked literal text.
autodoc-pydantic renders the ``repr()`` of a field's ``Annotated`` metadata into the field's type, so lambdas, enum members, and ``FieldInfo`` instances leak punctuation into cross-reference targets — ``FieldInfo(annotation=NoneType, default_factory=<lambda>)``, or fragments like ``lambda>)]) <pkg.Model.field`` once reST has parsed the mangled text.
A target containing ``<``, ``>``, ``(``, ``)``, or quotes (or whitespace outside a subscript) is never linkable, so it renders as plain text rather than warning.

References that still cannot resolve but point at objects that never have documentation targets — module-level :class:`typing.TypeVar`\ s, :pep:`695` scoped type parameters (``def f[U](...)``), undocumented aliases, and dunder attributes appearing in rendered alias values — degrade to unlinked literal text instead of nitpick warnings.
The same applies to references that import cleanly but point into an external package absent from every intersphinx inventory (``HttpUrl`` from pydantic, which publishes no inventory): the object is real, but nothing can ever link it.

A bare name bound by a **plain-assignment union alias** in a package that merely shares this project's top-level root degrades too.
``lsst.resources``\ ’s ``ResourcePathExpression = str | ParseResult | ResourcePath | Path``, written into a documented ``lsst.images`` annotation, is the case that motivated this: Sphinx 9 emits its bare name as a ``py:class`` reference with no document context at all — reported from ``<unknown>:1``, with no ``refdoc``, ``py:module``, or ``py:class`` on the node — where Sphinx 8 rendered the same signature as unlinked plain text.
Unlike a :pep:`695` ``type`` statement or a ``TypeVar``, such an alias binds a bare union object that knows neither the name it was assigned to nor the module it was written in (its ``__module__`` reads ``types``, or ``typing`` from Python 3.14 on), so the registry of typing objects scanned out of the project's package roots records the module it found each alias in.
Only aliases found entirely *outside* this project's documented module prefixes degrade: an alias in one of the project's own modules should be documented as a ``py:data`` or ``py:type`` object instead, so it keeps warning — and once it is documented, the role-mismatch rung above links the reference rather than degrading it.
Every hit for the name must also be the identical object, so a re-export chain resolves while one name meaning *different* unions in different modules keeps warning, as does a name no scanned module binds at all.

A bare name that is not importable from the page's own module is looked up once more through the **MRO of the class the reference was rendered inside**, trying each base class's defining module in turn (``builtins`` excepted).
This catches docstrings inherited from external base classes: a Pydantic model documented with ``:inherited-members:`` picks up ``pydantic.BaseModel.model_config``'s docstring, which refers to a bare ``ConfigDict`` — a name only Pydantic's own modules import, so the page's ``py:module`` namespace can never resolve it.
Resolving it through ``pydantic.main`` feeds the same degrade paths above, so the reference renders as literal text rather than one warning per model page.
This rung runs last, so a bare name that also names a project object still links to it.
Every MRO ends at :class:`object`, so ``builtins`` is skipped deliberately: otherwise any bare name colliding with a builtin (``input``, ``min``) would resolve on a class page and de-warn a possible typo.
Builtins that *should* link are intersphinx's job, not this rung's.

An inherited docstring writes about its own class's *members* too, not only about the names its module imports, so a bare name that no MRO module namespace has is looked up once more as an **attribute of an MRO class** — and the reference is retried against intersphinx under the fully-qualified name of the class that *defines* the attribute.
``lsst.daf.butler``\ ’s ``FormatterV2.write_local_file`` is the case that motivated this: its docstring refers to a bare ``to_bytes``, and a subclass that overrides ``write_local_file`` without writing a docstring of its own inherits that text — bare reference and all — onto a page in another package.
The rebuilt name (``lsst.daf.butler.FormatterV2.to_bytes``) is the one the base project's inventory documents, so the reference becomes a real link whenever that inventory is configured; the bare name alone never gets there, because a member name is rarely unique across inventories.\ [#members]_
Without such an inventory the resolved attribute reaches the external-object degrade above instead, and renders as literal text.
Bare names that *are* builtins are skipped here whatever class defines them: a docstring's ``dict`` means the builtin type, not the deprecated ``pydantic.BaseModel.dict`` method it collides with.

.. [#members] ``py:method`` and ``py:property`` inventory entries are searched only for these rebuilt names, so bare-name matching elsewhere in the ladder is unaffected.

Failing that, the bare name is looked up in the **top-level packages the MRO's classes come from** — every already-imported module under those package roots is scanned for the name (``builtins`` excluded again, and the scan is cached per build).
Pydantic field pages need this rung: the annotation parser splits a field's rendered ``Annotated[str, FieldInfo(annotation=NoneType, required=True, …)]`` type into its parts and emits a bare ``FieldInfo`` reference, but ``FieldInfo`` is exposed by neither ``pydantic`` nor ``pydantic.main``\ [#fieldinfo]_ — only by ``pydantic.fields``, which the MRO never names.
Because the reference resolves, the same external-object degrade above applies and it renders as literal text instead of warning on every field.
A name that several modules under those roots bind to *different* objects is treated as unresolved, and so is a name no module binds at all, so typos keep warning.

.. [#fieldinfo] ``pydantic.main`` imports it only under ``TYPE_CHECKING``, so it is not a runtime attribute of that module.

An object that this project defines only under a **private module path** degrades just like an external one.
A Pydantic field annotation routinely names a serialization model that lives in an internal module (``lsst.images._transforms._transform.MappingSerializationModel``) and is deliberately never re-exported.
Sphinx 9 emits a ``py:class`` reference for such a name — as a bare name on the field's page, or as a fully-qualified name with no document context at all\ [#context]_ — where Sphinx 8 rendered the same signature as unlinked plain text.
The object is real and imports cleanly, but no public documentation target for it can ever be created, so the reference renders as literal text.
The gate is the *module path*, not the object: a project-local object degrades only when some segment of its defining module path starts with an underscore.
Project-local objects under wholly public module paths — the ones that *should* be exported and documented but aren't — keep warning, and so do names that fail to import at all, private path or not.

.. [#context] Sphinx reports those from ``<unknown>:1``. This rung only reinterprets an object that the rungs above it already resolved, so it needs no document or module context of its own and widens nothing about what resolves.

Last of all, a target that is a **fragment of the documented class's own** ``Annotated`` **metadata** degrades to literal text.
The mangled-target rule above catches a leaked ``repr()`` that cannot be Python at all; when the same rendering *does* parse, Sphinx splits it into syntactically clean pieces and emits a reference for each one, so three more shapes reach the end of the ladder:

- ``Ge`` and ``Le`` — the ``annotated_types`` constraint objects Pydantic puts in a field's metadata for ``Field(ge=…, le=…)``, which surface through the ``repr()`` of the field's ``FieldInfo``. Their package is in none of the model's MRO roots, so the scan above never sees them.
- ``file`` — Sphinx renders *dataclass* metadata by stringifying each field value instead of by ``repr()``, so Pydantic's ``FilePath`` (``Annotated[Path, PathType('file')]``) renders as ``PathType(path_type=file)`` and the unquoted value is left looking like a name. It is a value fragment: no object of that name exists anywhere.
- ``ExecutionPhase.PENDING`` — enum members written into the metadata of an annotation Sphinx renders from its *source text*\ [#source]_, which unparse to dotted targets. The bare enum name resolves through the MRO rung above, but an attribute path on it is a name in no scanned namespace.

Metadata says how a value is validated; it is not a reference to anything, and none of these fragments can ever have a documentation target.
So the names that *this* class's metadata renders are rebuilt — from the metadata objects the way Sphinx renders them, and from unevaluated source-text annotations by reading their metadata positions — and a target among them renders as literal text.
The set is per class and is consulted only after every resolution rung has already failed, so this rung resolves nothing, adds no lookup surface, and raises no ambiguity question: a name that no metadata rendering of the class in question contains is left to warn, typo of a real fragment or not.
The annotated *type* is deliberately excluded, so it keeps following the ordinary ladder.

.. [#source] ``sphinx.util.typing.get_type_hints`` falls back to a class's raw ``__annotations__`` when evaluating them raises, and autodoc first copies each base class's *source* annotations onto the class — which is enough to make that fallback fire on a Pydantic model. Under ``from __future__ import annotations`` those raw annotations are :pep:`563` strings, so the annotation is rendered exactly as written.

The same fragment family reaches a **type alias's own page**, where the reference carries no ``py:class`` context for that rung to read — only the ``py:module`` of the module the alias is documented from.
Safir's ``type IvoaIsoDatetime = Annotated[datetime, BeforeValidator(…), PlainSerializer(…, when_used="json")]`` is the case that motivated this: Sphinx renders the alias's whole value onto its stub page — and into every signature the alias annotates, since an assignment-style alias knows neither its own name nor its module — leaking ``PydanticUndefined``, the repr of ``BeforeValidator``\ ’s sentinel default, and a bare ``json`` from the unquoted ``when_used`` value.
A module-scoped sibling index therefore rebuilds the fragments that the ``Annotated`` aliases of the reference's ``py:module`` context render, covering both alias spellings: a :pep:`695` ``type`` statement whose value is (or contains) an ``Annotated`` form, and an assignment-style ``Annotated`` alias.
It resolves nothing either, and is consulted only after the class-scoped rung has failed as well, so the guardrail is the same one module out — a name that no alias of that module renders keeps warning, and a fragment of one module's alias does not degrade under another module's context.

Anything else is left alone, so genuine mistakes (a typo'd module path that fails to import, a reference to something in this project's public API that should be exported and documented but isn't) still surface as nitpick warnings.

Sub-extensions
==============

``documenteer.ext.autotypes`` is an umbrella over three sub-extensions, each a Sphinx extension in its own right, split by the problem each one solves:

``documenteer.ext.autotypes.documenters``
   Rendering: the ``autotype`` documenter for :pep:`695` aliases, and the docstring recovery for ``Annotated`` and ``type`` aliases.

``documenteer.ext.autotypes.compat``
   Compatibility shims for other packages in the ecosystem: sphinx-automodapi_\ ’s object classification and its locality test for ``Annotated`` aliases, sphinx-click's ``mock`` import, the signature guard that keeps callable ``data`` objects in Sphinx 9 builds, and the legacy documenter registration that keeps non-field members on autodoc-pydantic_ model pages\ [#compat]_.

``documenteer.ext.autotypes.xrefs``
   Cross-reference policy: the ``missing-reference`` resolution ladder described above, and the ``py:module`` targets for modules documented by ``automodapi`` with ``:no-main-docstr:``.

Enabling ``documenteer.ext.autotypes`` (as ``documenteer.conf.guide`` does) enables all three, and is the recommended configuration.
A project that wants only one of these domains can name that sub-extension in ``extensions`` instead; each one sets up independently.

.. [#compat] Ideally ``documenteer.ext.autotypes.compat``\ ’s functionality will be upstreamed into the respective packages it shims, and this package can be dropped in a future Documenteer release.
