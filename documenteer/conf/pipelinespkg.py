"""Sphinx configuration for a single-package documentation builds for packages
in pipelines.lsst.io.

These configurations build upon `documenteer.conf.pipelines`.

To use this configuration, projects need to import this module's contents
into their Sphinx :file:`conf.py` and override configuration related to the
project's name:

.. code-block:: python

   from documenteer.conf.pipelinespkg import *


   project = "example"
   html_theme_options['logotext'] = project
   html_title = project
   html_short_title = project

Replace "example" with the name of the current package.

You can set, or override, additional Sphinx configurations after the
``documenteer`` import in your Sphinx :file:`conf.py` file.

.. note::

   This configuration is only used for single-package builds.
   It doesn't affect the pipelines.lsst.io build.
"""

# Derive configuration from the full-stack documentation build
from .pipelines import *  # noqa: F401 F403


# ============================================================================
# todo extension configuration
# ============================================================================
# Show todo directives in the development documentation for single packages.
todo_include_todos = True
