Autotypes plain-alias test
==========================

.. automodule:: aliasroot.documented
   :members:

Bare references to plain-assignment union aliases, one per side of the
external gate the degrade applies:

- `PathExpression` is defined in a package that shares this project's
  top-level root without being documented by it, so no target for it can
  ever exist here and the reference degrades to unlinked literal text.
- `LocalAlias` is defined under one of this project's own documented module
  prefixes, so it should be documented rather than degraded and the
  reference keeps warning.
- `PathExpresion` is a typo that names no alias in any scanned namespace,
  so it keeps warning as well.
