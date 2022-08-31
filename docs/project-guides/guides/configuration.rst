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
To use Documenteer's configuration pre-sets, import the |documenteer.conf.guide| module into it, and then override the details specifically related to your project:

.. code-block:: python
   :caption: conf.py

   from documenteer.conf.guide import *

   # General information about the project.
   project = "Example"
   copyright = (
       "2015-2022 "
       "Association of Universities for Research in Astronomy, Inc. (AURA)"
   )

   # The version info for the project you're documenting, acts as replacement for
   # |version| and |release|, also used in various other places throughout the
   # built documents.
   version = "1.0.0"
   release = version

   # HTML theme option overrides
   html_theme_options["icon_links"][0]["url"] = "https://github.com/lsst/example"
   html_theme_options["logo"]["text"] = project

   # The name for this set of Sphinx documents.  If None, it defaults to
   # "<project> v<release> documentation".
   html_title = project

   # A shorter title for the navigation bar.  Default is the same as html_title.
   html_short_title = project

Extending the Sphinx extension
==============================

The basic configuration, shown above, sets up Sphinx to work well for most types of Rubin documentation projects.
You will likely need to extend that configuration, though.
This sections describes a few common scenarios.

In general, structure your customizations so that they add to the configuration presets from |documenteer.conf.guide|.
If the configuration variable is a list or a dictionary, try to append to that list or dictionary rather than reassigning the whole variable.

Setting the version from your Python package
--------------------------------------------

Rather than manually setting the ``version`` configuration variable, you can set it so match your Python project's version string.
One approach is to use `importlib.metadata.version`:

.. code-block:: python
   :caption: conf.py

   from importlib.metadata import version as get_version

   from documenteer.conf.guide import *

   # The version info for the project you're documenting, acts as replacement for
   # |version| and |release|, also used in various other places throughout the
   # built documents.
   version = get_version("example")
   release = version

   # ... include other conf.py configurations

Change ``example`` to your Python package's name.

Adding a package to Intersphinx
-------------------------------

One scenario is adding additional projects to the Intersphinx_ configuration.
For example, to add the Python standard library so that built-in Python APIs can be referenced:

.. code-block:: python
   :caption: conf.py

   from documenteer.conf.guide import *

   intersphinx_mapping["python"] = ("https://docs.python.org/3", None)

To additionally add the LSST Science Pipelines:

.. code-block:: python
   :caption: conf.py

   from documenteer.conf.guide import *

   intersphinx_mapping["python"] = ("https://pipelines.lsst.io", None)

Adding a Sphinx extension
-------------------------

You can add additional `Sphinx extensions`_ to your Sphinx build to make use of custom reStructuredText directives and roles.
To add a new extension, append to the ``extensions`` list:

.. code-block:: python
   :caption: conf.py

   from documenteer.conf.guide import *

   extensions.extend(["sphinx-click"])

Remember that additional packages may need to be added to your project's Python dependencies (such as in a ``requirements.txt`` or ``pyproject.toml`` file).

.. |documenteer.conf.guide| replace:: :doc:`documenteer.conf.guide <configuration-preset>`

.. _Sphinx extensions: https://www.sphinx-doc.org/en/master/develop.html

.. _Intersphinx: https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html
