:og:description: Documenteer provides Sphinx extensions, configurations, and tooling for Rubin Observatory documentation projects.
:html_theme.sidebar_secondary.remove:

###########
Documenteer
###########

**Sphinx extensions, configurations, and tooling for Rubin Observatory documentation projects.**

Documenteer is developed on GitHub at https://github.com/lsst-sqre/documenteer.
Find other versions of the documentation at https://documenteer.lsst.io/v

.. _pip-install:
.. _installation:

Installation
============

.. tab-set::

   .. tab-item:: pip

      The core package provides Documenteer's :doc:`Sphinx extensions </sphinx-extensions/index>`:

      .. code-block:: sh

         pip install documenteer

      To use Documenteer's configurations for specific Rubin documentation use cases, you'll need to install Documenteer with specific "extras" to bring in the necessary dependencies.

      For :doc:`Rubin user guide projects </guides/index>`:

      .. code-block:: sh

         pip install "documenteer[guide]"

      .. _install-technotes:

      For :doc:`technote projects </technotes/index>`:

      .. code-block:: sh

         pip install "documenteer[technote]"

   .. tab-item:: conda

      Documenteer is available from `conda-forge`_ for Conda_ users.
      First, enable the conda-forge channel:

      .. code-block:: sh

         conda config --add channels conda-forge
         conda config --set channel_priority strict

      The core package provides Documenteer's :doc:`Sphinx extensions </sphinx-extensions/index>`:

      .. code-block:: sh

         conda install documenteer

      To use Documenteer's configurations for specific Rubin documentation use cases, you'll need to install Documenteer with specific "extras" to bring in the necessary dependencies.

      To install Documenteer for technote projects:

      .. code-block:: sh

         conda-install lsst-documenteer-technote

Project guides
==============

Documenteer provides centralized Sphinx configuration and support for Rubin Observatory documentation projects.
This section describes how to use Documenteer for specific types of projects, from single-page technical notes to user guides.

.. toctree::
   :maxdepth: 2

   Rubin user guides <guides/index>
   Technical notes <technotes/index>

Sphinx extensions
=================

Documenteer provides several Sphinx extensions.
These extensions are designed for Rubin Observatory documentation projects, but are may be generally useful:

.. toctree::
   :maxdepth: 2

   sphinx-extensions/index

.. toctree::
   :hidden:

   changelog

Developer guide
===============

.. toctree::
   :maxdepth: 2

   dev/index
