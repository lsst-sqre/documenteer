############################################################
Documenteer for LSST Science Pipelines (stack) documentation
############################################################

The `LSST Science Pipelines`_ is an EUPS-managed stack.
Documenteer includes specific command-line tools and Sphinx configurations to build documentation for both multi-package stacks (such as pipelines.lsst.io_) as well as individual or stand-alone stack packages (such as astro-metadata-translator.lsst.io_).
Documenteer also includes Sphinx extensions to help document domain-specific topics, such as LSST Tasks.

.. _LSST Science Pipelines:
.. _pipelines.lsst.io: https://pipelines.lsst.io
.. _astro-metadata-translator.lsst.io: https://astro-metadata-translator.lsst.io

.. toctree::
   :maxdepth: 2

   install
   build-overview
   stack-docs-cli
   package-docs-cli
   configuration
   cpp-api-linking
