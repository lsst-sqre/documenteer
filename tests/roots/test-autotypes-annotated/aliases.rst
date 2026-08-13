Alias-metadata fragments
========================

.. automodule:: aliaspkg

Both alias spellings, documented from the package that re-exports them,
plus a function annotated with the assignment-style one. Sphinx renders
each alias's whole ``Annotated`` value — validator and serializer metadata
included — into the alias's own page and into that signature, where a
reference carries no ``py:class`` context at all, only this module's
``py:module``.

.. autotype:: aliaspkg.IsoDatetime

.. autodata:: aliaspkg.TrimmedName

.. autofunction:: aliaspkg.register
