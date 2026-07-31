Autotypes test
==============

The `autotypespkg` package (a reference to a module documented with
``:no-main-docstr:``, so automodapi creates no ``py:module`` target for
it) provides `Registry` (a bare name resolved via the module context of
this page's automodapi) and the `StampValue` alias.

A class-relative reference: `Registry.get`.

A Pydantic model's ``model_config``, documented the way a
``:inherited-members:`` automodapi template renders it: the attribute is
set on an intermediate base without a docstring, so autodoc inherits
`pydantic.BaseModel`'s own ``model_config`` docstring, which references a
bare ``ConfigDict``. autodoc-pydantic's model documenter hides
``model_config``, so it is documented here with plain ``autoclass``.

.. autoclass:: autotypespkg.StampSettings
   :members: model_config
   :noindex:

.. automodapi:: autotypespkg
   :no-main-docstr:
   :no-inheritance-diagram:
   :include-all-objects:
