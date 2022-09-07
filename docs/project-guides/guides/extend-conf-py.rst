##########################
Extending conf.py directly
##########################

The basic configurations, through :file:`documenteer.toml` and |documenteer.conf.guide|, set up Sphinx to work well for most types of Rubin documentation projects.
You will likely need to extend that configuration, though.
This page describes a few common scenarios.

In general, structure your customizations so that they add to the configuration presets from |documenteer.conf.guide|.
If the configuration variable is a list or a dictionary, try to append to that list or dictionary rather than reassigning the whole variable.

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
