Autotypes private-path test
===========================

.. automodule:: privatepkg
   :members:

Fully-qualified references that no rung above the private-path degrade
can resolve, one per side of that rung's gate:

- `privatepkg._impl.PrivateOnly` imports to a real project-local object
  under a private module path, so it degrades to unlinked literal text.
- `privatepkg.helpers.PublicUndocumented` imports to a real project-local
  object under a wholly public module path, so it keeps warning.
- `privatepkg._impl.PrivateOnyl` is a typo that imports to nothing, so it
  keeps warning as well.
