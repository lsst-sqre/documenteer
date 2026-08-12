Autotypes callable-singleton test
=================================

``auth_dependency`` is a module-level callable singleton. Sphinx 9 gives
``data`` objects no signature slot, so the signature tuple
sphinx-autodoc-typehints returns for it has nowhere to go and the object
is dropped from the build entirely unless the compat guard intervenes.

.. automodule:: singletonpkg
   :members:
