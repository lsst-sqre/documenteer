##################################
Sphinx configuration for technotes
##################################

Documenteer provides centralized configuration for technotes.
To use these configurations, you must first install Documenteer with the "technote" extra, see :ref:`installation guide <install-technotes>`.

.. _technote-basic-conf:

Basic configuration
===================

To use Documenteer's configuration in a Sphinx technote project, create a :file:`conf.py` file:

.. code-block:: python

   from documenteer.conf.technote import *

This configuration uses content from the :file:`metadata.yaml` file, also in the technote project, to set information such as the title and authors.

.. _technote-custom-conf:

Extending your technote's configuration
=======================================

You can enhance and customize your technote's configuration by adding additional lines of Python, after the ``import`` statement in your :file:`conf.py` file.
These lines extend, and even replace statements in the configuration provided by Documenteer, which you can see in :ref:`technote-conf-source`, below.

The follow sections point out some common configuration tasks.
For more information about Sphinx configuration in general, see the `Sphinx documentation`_.

.. _Sphinx documentation: https://www.sphinx-doc.org/en/master/usage/configuration.html

Adding a package to Intersphinx
-------------------------------

One scenario is adding additional projects to the Intersphinx_ configuration.
For example, to add the Python standard library so that built-in Python APIs can be referenced:

.. code-block:: python

   from documenteer.conf.technote import *

   intersphinx_mapping["python"] = ("https://docs.python.org/3", None)

To additionally add the LSST Science Pipelines:

.. code-block:: python

   from documenteer.conf.technote import *

   intersphinx_mapping["python"] = ("https://pipelines.lsst.io", None)

Adding a Sphinx extension
-------------------------

You can add additional `Sphinx extensions`_ to your Sphinx build to make use of custom reStructuredText directives and roles.
To add a new extension, append to the ``extensions`` list:

.. code-block:: python

   from documenteer.conf.technote import *

   extensions.extend(["sphinx-click"])

Remember that if an additional package needs to be installed, add that dependency to the technote's :file:`requirements.txt` file.

.. _technote-conf-source:

Configuration source reference
==============================

.. literalinclude:: ../../src/documenteer/conf/technote.py
