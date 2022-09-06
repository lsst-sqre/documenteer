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
Sphinx imports Python packages to generate documentation for their APIs.

The :ref:`main documentation repository <developer:stack-docs-system-main-repo>` (`pipelines_lsst_io`_) has an EUPS table file.
This table file defines all the Stack packages that should be set up and that are available for inclusion in the Stack documentation build.
See :ref:`developer:add-to-pipelines-lsst-io` for details.

.. _pipelines-build-doxygen:

Doxygen build
=============

Doxygen_ extracts information from the source code to generate the C++ API reference.
Documenteer runs Doxygen as a step in the |stack-docs| command.

First, Documenteer identifies which packages contain a :file:`doc/doxygen.conf.in` file.
Any package containing a Doxygen configuration stub file, even if empty, is presumed to potentially contain source material the C++ API reference.

Second, Documenteer constructs a Doxygen configuration.
By default, the :file:`include` directory of each relevant package is included in the ``INPUT`` Doxygen configuration tag.
Individual packages can also add other paths to the ``INPUT`` and ``IMAGE_PATH`` tags, remove paths (``EXCLUDE`` or ``EXCLUDE_PATTERNS`` tags),  or exclude symbols (``EXCLUDE_SYMBOLS`` tag).

Finally, Documenteer uses this combined Doxygen configuration to run the :command:`doxygen` command to generate an HTML site and tag file that exclusively documents the C++ API reference.
Sphinx copies the Doxygen site into the :file:`cpp-api` directory during its build so that the Doxygen-generated API reference effectively becomes an sub-site of the Sphinx-rendered site.
The pipelines.lsst.io documentation project has a special :rst:role:`lsstcc` role, created through doxylink_ extension, using the Doxygen tag file, that allows reStructuredText content to link to C++ API reference pages in the Doxygen site.

For more information about Documenteer's built-in Doxygen build, see the `documenteer.stackdocs.doxygen` module, and the `~documenteer.stackdocs.doxygen.run_doxygen` and `~documenteer.stackdocs.doxygen.DoxygenConfiguration` APIs in particular.
From a documentation writer's perspective, see also: :doc:`cpp-api-linking`.

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

.. _pipelines-build-related:

Related reading
===============

Documenteer documentation:

- :doc:`stack-docs-cli`

Other LSST sites:

- `DMTN-030 Science Pipelines Documentation Design`_
- :ref:`developer:stack-documentation-overview`
