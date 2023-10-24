#############################
package-docs command-line app
#############################

Use the :command:`package-docs` command-line app to compile the documentation for a single Stack package.
This is useful for local previewing during development, though links to other packages will be broken.
For full https://pipelines.lsst.io site builds, use the :doc:`stack-docs <stack-docs-cli>` app instead.

.. seealso::

   `Building single-package documentation locally <https://developer.lsst.io/stack/building-single-package-docs.html>`__ (DM Developer Guide)

.. click:: documenteer.stackdocs.packagecli:main
  :prog: package-docs
  :show-nested:
