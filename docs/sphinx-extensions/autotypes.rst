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

.. [#click] It also repairs sphinx-click's ``mock`` import, which can break under Sphinx 9 with ``TypeError: 'module' object is not callable`` when another extension imports ``sphinx.ext.autodoc.mock``.

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

A bare name that is not importable from the page's own module is looked up once more through the **MRO of the class the reference was rendered inside**, trying each base class's defining module in turn (``builtins`` excepted).
This catches docstrings inherited from external base classes: a Pydantic model documented with ``:inherited-members:`` picks up ``pydantic.BaseModel.model_config``'s docstring, which refers to a bare ``ConfigDict`` — a name only Pydantic's own modules import, so the page's ``py:module`` namespace can never resolve it.
Resolving it through ``pydantic.main`` feeds the same degrade paths above, so the reference renders as literal text rather than one warning per model page.
This rung runs last, so a bare name that also names a project object still links to it.
Every MRO ends at :class:`object`, so ``builtins`` is skipped deliberately: otherwise any bare name colliding with a builtin (``input``, ``min``) would resolve on a class page and de-warn a possible typo.
Builtins that *should* link are intersphinx's job, not this rung's.

Anything else is left alone, so genuine mistakes (a typo'd module path that fails to import, a reference to something in this project that should be exported and documented but isn't) still surface as nitpick warnings.

Sub-extensions
==============

``documenteer.ext.autotypes`` is an umbrella over three sub-extensions, each a Sphinx extension in its own right, split by the problem each one solves:

``documenteer.ext.autotypes.documenters``
   Rendering: the ``autotype`` documenter for :pep:`695` aliases, and the docstring recovery for ``Annotated`` and ``type`` aliases.

``documenteer.ext.autotypes.compat``
   Compatibility shims for other packages in the ecosystem: sphinx-automodapi_\ ’s object classification and its locality test for ``Annotated`` aliases, and sphinx-click's ``mock`` import\ [#compat]_.

``documenteer.ext.autotypes.xrefs``
   Cross-reference policy: the ``missing-reference`` resolution ladder described above, and the ``py:module`` targets for modules documented by ``automodapi`` with ``:no-main-docstr:``.

Enabling ``documenteer.ext.autotypes`` (as ``documenteer.conf.guide`` does) enables all three, and is the recommended configuration.
A project that wants only one of these domains can name that sub-extension in ``extensions`` instead; each one sets up independently.

.. [#compat] Ideally ``documenteer.ext.autotypes.compat``\ ’s functionality will be upstreamed into the respective packages it shims, and this package can be dropped in a future Documenteer release.
