.. default-domain:: rst

##########################################################################
The autodocreset extension for resetting automodapi's autodoc enhancements
##########################################################################

The `sphinx-automodapi`_ extension includes an ``autodoc_enhancements`` module that replaces autodoc's built-in "attr getter" for ``type``.
While this enhancement is useful for Python meta programming, it can also be incompatible with Pybind11 static properties, which are present in the LSST Science Pipelines.
This Sphinx extension resets automodapi's autodoc enhancements and is included by default in the :doc:`Pipelines Sphinx configuration </pipelines/configuration>`.

.. _sphinx-automodapi: https://sphinx-automodapi.readthedocs.io/en/latest/

To use this directive, add ``documenteer.ext.autocppapi`` after both autodoc and automodapi:

.. code-block:: python

   extensions = [
       "sphinx.ext.autodoc",
       "sphinx_automodapi.automodapi",
       "sphinx_automodapi.smart_resolver",
       "documenteer.ext.autodocreset",
   ]
