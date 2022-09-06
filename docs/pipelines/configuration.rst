############################################
Sphinx configuration for stacks and packages
############################################

Documenteer provides pre-made Sphinx configurations for stack packages and stack documentation projects.
To use these configurations, you must install Documenteer with the "pipelines" extra, see :doc:`install`.

.. _pipelines-conf:

Sphinx configuration for stack documentation projects
=====================================================

The configuration module for a stack documentation project, such as pipelines.lsst.io_ is ``documenteer.conf.pipelines``.
To use these configurations, the content of the Sphinx :file:`conf.py` file should be:

.. code-block:: python

   from documenteer.conf.pipelines import *

.. note::

   This configuration is specialized for the pipelines.lsst.io_ documentation project.
   To adapt and customize it for other projects, you will likely need to change the ``project`` variable to the name of the specific stack:

   .. code-block:: python

      from documenteer.conf.pipelines import *

      project = "example"
      html_theme_options["logotext"] = project
      html_title = project
      html_short_title = project

   You can change the name after importing the ``documenteer.conf.pipelines`` configuratio module in your :file:`conf.py` file.
   See the :ref:`source for documenteer.conf.pipelines <pipelines-conf-source>` for additional configuartion options.

.. _pipelinespkg-conf:

Sphinx configuration for packages
=================================

Individual packages in a stack also have Sphinx configurations to facilitate single-package builds for development.
The configurations for individual packages is provided by the ``documenteer.conf.pipelines`` file.

To use this configuration, projects need to import this module's contents
into their Sphinx :file:`conf.py` and override configuration related to the
project's name:

.. code-block:: python

   from documenteer.conf.pipelinespkg import *


   project = "example"
   html_theme_options["logotext"] = project
   html_title = project
   html_short_title = project

Replace "example" with the name of the current package.

You can set, or override, additional Sphinx configurations after the
``documenteer`` import in your Sphinx :file:`conf.py` file.

.. note::

   This configuration is only used for single-package builds.
   It doesn't affect the stack build (such as pipelines.lsst.io_).

Configuration source reference
==============================

.. _pipelines-conf-source:

documenteer.conf.pipelines source
---------------------------------

.. literalinclude:: ../../src/documenteer/conf/pipelines.py

.. _pipelinespkg-conf-source:

documenteer.conf.pipelinespkg source
------------------------------------

.. literalinclude:: ../../src/documenteer/conf/pipelinespkg.py
