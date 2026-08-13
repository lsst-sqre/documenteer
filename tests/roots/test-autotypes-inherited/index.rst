Autotypes inherited-docstring test
==================================

``StampFormatter.write_local_file`` has no docstring of its own, so
autodoc documents it with the external base class's docstring — whose
bare method reference is written in the base class's own module context,
not this package's. That reference is the only one on this page, so the
build assertions can find it by name.

.. automodule:: inheritpkg
   :members:
