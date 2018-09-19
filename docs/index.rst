###########
Documenteer
###########

**Sphinx extensions, configurations, and tooling for LSST Data Management documentation projects.**

Documenteer is developed on GitHub at https://github.com/lsst-sqre/documenteer.

.. toctree::
   :maxdepth: 1

   changelog

Pipelines projects
==================

.. toctree::
   :maxdepth: 1

   pipelines/install
   pipelines/build-overview
   pipelines/stack-docs-cli
   pipelines/package-docs-cli

Sphinx extensions
=================

.. toctree::
   :maxdepth: 1

   sphinxext/lssttasks

Python API reference
====================

.. automodapi:: documenteer.sphinxconfig.stackconf
   :no-main-docstr:

.. automodapi:: documenteer.sphinxconfig.technoteconf
   :no-main-docstr:

.. automodapi:: documenteer.sphinxconfig.utils
   :no-main-docstr:

.. automodapi:: documenteer.sphinxext
   :no-main-docstr:

.. FIXME I couldn't get intersphinx to resolve inherited members, and no-inherited-members doesn't work, hence I'm skipping this API.

.. automodapi:: documenteer.sphinxext.bibtex
   :no-main-docstr:
   :no-inherited-members:
   :skip: LsstBibtexStyle

.. automodapi:: documenteer.sphinxext.jira
   :no-main-docstr:

.. automodapi:: documenteer.sphinxext.lsstdocushare
   :no-main-docstr:

.. automodapi:: documenteer.sphinxext.mockcoderefs
   :no-main-docstr:

.. FIXME I couldn't get intersphinx to resolve inherited members, and no-inherited-members doesn't work, hence I'm skipping this API.

.. automodapi:: documenteer.sphinxext.packagetoctree
   :no-main-docstr:
   :no-inherited-members:
   :skip: ModuleTocTree
   :skip: PackageTocTree

.. automodapi:: documenteer.requestsutils
   :no-main-docstr:

.. automodapi:: documenteer.sphinxrunner
   :no-main-docstr:
