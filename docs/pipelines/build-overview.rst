.. _pipelines-build-overview:

##############################################
Overview of the pipelines.lsst.io build system
##############################################

This page is a high-level overview of the tools and processes for building the `pipelines.lsst.io`_ documentation.

To learn how to build the `pipelines.lsst.io`_ site in practice, see :ref:`developer:local-pipelines-lsst-io-build`.
For more background on contributing to `pipelines.lsst.io`_ documentation, see :ref:`developer:stack-documentation-overview`.

.. _pipelines-build-documenteer:

Documenteer
===========

Documenteer is the Python package that provides tooling for LSST DM’s Sphinx-based documentation projects, including Stack user guides such as `pipelines.lsst.io`_.
Documenteer plays four roles:

- Documenteer manages and versions the Python dependencies needed to build Sphinx documentation.
  The :file:`requirements.txt` file in the `pipelines_lsst_io`_ repository refers to a specific release of Documenteer, which in turn specifies its own Python dependencies.

- Documenteer provides centralized Sphinx_ configurations for both the `pipelines_lsst_io`_ repository and individual packages.

- Documenteer provides Sphinx_ extensions built specifically for LSST DM needs.

- Documenteer provides the |stack-docs| command-line app that runs the Sphinx_ documentation build process (Documenteer also provides the related |package-docs| app for :ref:`developer:single-package documentation builds <build-package-docs>`).

.. _pipelines-build-setup:

Stack build and set up
======================

The prerequisite for the Stack documentation build is that the Stack is already built and set up.
Not only does this make the Stack importable so that Sphinx can introspect the Python APIs, it also means that Doxygen has already run (through SCons_\ /`sconsUtils`_ and `lsstDoxygen`_) and generated XML files with C++ API descriptions.

The :ref:`main documentation repository <developer:stack-docs-system-main-repo>` (`pipelines_lsst_io`_) has an EUPS table file.
This table file defines all the Stack packages that should be set up and that are available for inclusion in the Stack documentation build.
See :ref:`developer:add-to-pipelines-lsst-io` for details.

.. _pipelines-build-linking:

Package documentation linking
=============================

The next step of the build is to run |stack-docs|, from Documenteer.

The |stack-docs| app begins by discovering packages that are set up by EUPS and that also have :ref:`doc/manifest.yaml <developer:docdir-manifest-yaml>` files.
Following the :ref:`doc/manifest.yaml <developer:docdir-manifest-yaml>` file, |stack-docs| symlinks the :ref:`module <developer:docdir-module-doc-directories>` and :ref:`package documentation directories <developer:docdir-package-doc-directory>` into the :file:`modules/` and :file:`packages/` directories of the `pipelines_lsst_io`_ repository.

.. _pipelines-build-sphinx:

The Sphinx build
================

Next, |stack-docs| runs the Sphinx_ build on the `pipelines_lsst_io`_ repository.
This is different from most projects that use a :file:`Makefile` and Sphinx_\ ’s builtin :command:`sphinx-build` app.
|stack-docs| is an all-in-one front-end designed and engineered for building the `pipelines.lsst.io`_ site.

The :file:`conf.py` file in `pipelines_lsst_io`_ configures the Sphinx_ build, which in turn uses Documenteer_\ ’s centralized Sphinx_ configuration API.

Since the documentation content from all the packages is symlinked into the `pipelines_lsst_io`_ repository, a single Sphinx_ build generates the entire `pipelines.lsst.io`_ site.

.. _pipelines-build-pyapi:

Python API reference
====================

The `automodapi`_ directives in :ref:`module homepages <developer:module-homepage>` generate the Python API reference documentation.
Specifically, `automodapi`_ introspects the APIs in the given Python module and creates stub files in the :file:`py-api` directory that contain ``autodoc`` directives that generate the documentation page for each API.
The `numpydoc`_ extension transforms docstrings before they are read by ``autodoc`` from the :ref:`numpydoc format <developer:numpydoc-format>` to Sphinx’s native docstring markup.

The :file:`py-api` directory is entirely transient.
In fact, the |stack-docs-clean| command will delete it.

See :ref:`developer:module-homepage` for more information on the `automodapi`_ directives.

.. _pipelines-build-cppapi:

C++ API reference
=================

The `breathe`_ directives in :ref:`module homepages <developer:module-homepage>` generate the C++ API reference documentation.
`breathe`_ consumes the XML created by Doxygen during the initial (SCons_\ /sconsUtils_) build of each Stack package.

See :ref:`developer:module-homepage` for more information on the `breathe`_ directives.

.. _pipelines-build-related:

Related reading
===============

Documenteer documentation:

- :doc:`stack-docs-cli`

Other LSST sites:

- `DMTN-030 Science Pipelines Documentation Design`_
- :ref:`developer:stack-documentation-overview`

.. |package-docs| replace:: :doc:`package-docs <package-docs-cli>`
.. |stack-docs| replace:: :doc:`stack-docs <stack-docs-cli>`
.. |stack-docs-build| replace:: :doc:`stack-docs build <stack-docs-cli>`
.. |stack-docs-clean| replace:: :doc:`stack-docs clean <stack-docs-cli>`

.. _`pipelines.lsst.io`: https://pipelines.lsst.io
.. _`pipelines_lsst_io`: https://github.com/lsst/pipelines_lsst_io
.. _Sphinx: http://www.sphinx-doc.org/en/master
.. _toctree: http://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-toctree
.. _`pipe_base`: https://github.com/lsst/pipe_base
.. _`pipe_supertask`: https://github.com/lsst/pipe_supertask
.. _`pex_config`: https://github.com/lsst/pex_config
.. _`package-docs`: https://documenteer.lsst.io/v/DM-14852/pipelines/package-docs-cli.html
.. _`sconsUtils`: https://github.com/lsst/sconsUtils
.. _`lsstDoxygen`: https://github.com/lsst/lsstDoxygen
.. _SCons: https://scons.org
.. _automodapi: http://sphinx-automodapi.readthedocs.io/en/latest/automodapi.html
.. _numpydoc: https://numpydoc.readthedocs.io/en/latest/index.html
.. _breathe: http://breathe.readthedocs.io/en/latest/index.html
.. _`sqre/infrastructure/documenteer`: https://ci.lsst.codes/blue/organizations/jenkins/sqre%2Finfrastructure%2Fdocumenteer/activity
.. _`SQR-006`: https://sqr-006.lsst.io
.. _`DMTN-030`:
.. _`DMTN-030 Science Pipelines Documentation Design`: https://dmtn-030.lsst.io
