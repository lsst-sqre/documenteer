###########################
stack-docs command-line app
###########################

Use the :command:`stack-docs` command-line app to compile the full https://pipelines.lsst.io site from the https://github.com/lsst/pipelines_lsst_io repository.
For single-package doc builds, use the
To preview the documentation for a single package during development, use the :doc:`package-docs <package-docs-cli>` app instead.

.. seealso::

   `Building the pipelines.lsst.io site locally <https://developer.lsst.io/stack/building-pipelines-lsst-io-locally.html>`__ (DM Developer Guide)

.. click:: documenteer.stackdocs.stackcli:main
  :prog: stack-docs
  :show-nested:
