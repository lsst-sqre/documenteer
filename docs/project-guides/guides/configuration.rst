##############################################################
Setting up the Documenteer configuration for Rubin user guides
##############################################################

Documenteer provides centralized configuration, |documenteer.conf.guide| for Rubin Observatory user guide websites created with Sphinx.
This page page shows how to add Documenteer as a Python dependency, install Documenteer's Sphinx configuration, and then customize that configuration.

Python dependency
=================

First, add ``documenteer`` and its ``guide`` extra as a dependency to your project.
How you do this depends on your project's packaging structure:

.. tab-set::

   .. tab-item:: pyproject.toml

      .. code-block:: toml
         :caption: pyproject.toml

         [project.optional-dependencies]
         dev = [
             "documenteer[guide]"
         ]

   .. tab-item:: requirements.txt

      .. code-block:: text
         :caption: requirements.txt

         documenteer[guide]

Create a basic conf.py Sphinx configuration file
================================================

At the root of your project's documentation, usually the ``docs`` directory for a software project or the root of a documentation-only repository, the :file:`conf.py` file configures Sphinx.
To use Documenteer's configuration pre-sets, import the |documenteer.conf.guide| module into it:

.. code-block:: python
   :caption: conf.py

   from documenteer.conf.guide import *

Create a basic documenteer.toml configuration file
==================================================

In the same directory as the :file:`conf.py` file, create a file called :file:`documenteer.toml`:

.. code-block:: toml
   :caption: documenteer.toml

   [project]
   title = "Example"
   copyright = "2015-2022 Association of Universities for Research in Astronomy, Inc. (AURA)"
   base_url = "https://example.lsst.io"
   github_url = "https://github.com/lsst/example"

The information from :file:`documenteer.toml` is used by the |documenteer.conf.guide| preset to configure values in :file:`conf.py` for Sphinx.

See :doc:`toml-reference` for more information.

.. tip::

   If your project is a Python package that uses :file:`pyproject.toml`, you can skip some of this metadata.
   See :doc:`pyproject-configuration`.

.. note::

   Curious about the ``toml`` syntax? Learn more at the `official TOML website <https://toml.io/en/>`__.
   Documenteer uses TOML for configuration to match Python's adoption of toml (such as for :file:`pyproject.toml`).

Next steps
==========

- If you are setting up a Python project, see :doc:`pyproject-configuration`.
- For additional Sphinx configuration control, see :doc:`extend-conf-py`.
