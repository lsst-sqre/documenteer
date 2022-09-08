##########################
Extending conf.py directly
##########################

The basic configurations, through :file:`documenteer.toml` and |documenteer.conf.guide|, set up Sphinx to work well for most types of Rubin documentation projects.
You will likely need to extend that configuration, though.
This page describes a few common scenarios.

Using the [sphinx] table in documenteer.toml
============================================

Before editing :file:`conf.py`, check the :doc:`toml-reference` to see if there's support for a particular Sphinx configuration.
For example, the ``[sphinx]`` table includes support for adding Sphinx extensions, adding projects to the Intersphinx_ mapping, among other capabilities.

If the configuration isn't supported by :file:`documenteer.toml`, you can edit the Sphinx :file:`conf.py` configuration file directly.

Editing conf.py
===============

When Sphinx runs, the :file:`conf.py` configuration file is "executed" so that all variables in the global namespace become Sphinx configurations.
The |documenteer.conf.guide| configuration presets populate the global namespace.
Therefore you can add or edit those configurations by setting variables after the import of |documenteer.conf.guide|.

For example, to change the number of times the linkcheck builder will try a URL:

.. code-block:: python
   :caption: conf.py

   from documenteer.conf.guide import *

   linkcheck_retries = 2

See the `list of Sphinx configuration in the Sphinx documentation <https://www.sphinx-doc.org/en/master/usage/configuration.html>`__.
Extensions can also declare additional configurations, see their documentation for listings.
