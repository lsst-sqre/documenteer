Autotypes Annotated-metadata test
=================================

.. automodule:: annotatedpkg

Each model below carries one sub-shape of the reference family that
Sphinx synthesizes out of ``Annotated`` metadata: an ``annotated_types``
constraint from a ``FieldInfo`` repr, an unquoted string value from a
dataclass metadata object, and enum members written into a source-text
annotation.

.. autopydantic_model:: annotatedpkg.SentryConfig
   :members:

.. autopydantic_model:: annotatedpkg.KafkaSettings
   :members:

.. autopydantic_model:: annotatedpkg.Job
   :members:

The same fragment family reaches a *type alias's* own page, where the
reference node carries only a ``py:module`` context:

.. toctree::

   aliases
