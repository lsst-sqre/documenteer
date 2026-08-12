Autotypes autodoc-pydantic member test
======================================

``StampConfig`` is documented by autodoc-pydantic's model documenter,
which is written against autodoc's legacy class-based API. Sphinx 9
registers its own built-in documenters for that API only when
``autodoc_use_legacy_class_based`` is enabled, so a legacy documenter
finds no documenter able to handle an ordinary method, classmethod, or
property and drops those members from the page.

The prose below refers to `StampConfig.deserialize`, the kind of
reference that breaks when the member is not documented.

.. autopydantic_model:: pydanticpkg.StampConfig
   :members:
