:html_theme.sidebar_secondary.remove:

###########
Documenteer
###########

**Sphinx extensions, configurations, and tooling for Rubin Observatory documentation projects.**

Documenteer is developed on GitHub at https://github.com/lsst-sqre/documenteer.

.. _pip-install:

Installation with pip
=====================

You can install Documenteer from PyPI with pip:

.. code-block:: sh

   pip install documenteer

For different applications, install Documenteer with specific "extras" to bring in the necessary dependencies.

.. _install-technotes:

For technote projects:

.. code-block:: sh

   pip install "documenteer[technote]"

For LSST Stack projects (such as https://pipelines.lsst.io and EUPS packages):

.. code-block:: sh

   pip install "documenteer[pipelines]"

See :doc:`/pipelines/install` for more information.

Installation with Conda
=======================

Documenteer is available from `conda-forge`_ for Conda_ users.
First, enable the conda-forge channel:

.. code-block:: sh

   conda config --add channels conda-forge
   conda config --set channel_priority strict

To install only the core documenteer package:

.. code-block:: sh

   conda install documenteer

To install documenteer for technote projects:

.. code-block:: sh

   conda-install lsst-documenteer-technote

To install documenteer for LSST Stack projects (such as https://pipelines.lsst.io and EUPS packages):

.. code-block:: sh

   conda-install lsst-documenteer-pipelines

Project guides
==============

Documenteer provides centralized Sphinx configuration and support for Rubin Observatory documentation projects.
This section describes how to use Documenteer for specific types of projects, from single-page technical notes to user guides, to LSST Science Pipelines package documentation.

.. toctree::
   :maxdepth: 3

   project-guides/index

Sphinx extensions
=================

Documenteer provides several Sphinx extensions.
These extensions are designed for Rubin Observatory documentation projects, but are may be generally useful:

.. toctree::
   :maxdepth: 2

   sphinx-extensions/index

Developer guide
===============

.. toctree::
   :maxdepth: 2

   dev/index

.. toctree::
   :hidden:

   changelog
