##############################
Sphinx extensions in technotes
##############################

Technotes include Sphinx extensions that provide additional features, like diagrams-as-code.
This page explains what extensions are included by default in Rubin technotes, and how to add additional extensions to your own technote as needed.

.. _technote-default-extensions:

Default extensions
==================

These extensions are included and pre-configured in all technotes:

:doc:`documenteer.ext.jira </sphinx-extensions/jira-reference>`
   This extension provides roles for linking to Jira issues.

:doc:`documenteer.ext.lsstdocushare </sphinx-extensions/docushare-reference>`
   This extension provides roles for linking to Rubin Observatory documents based on their handle.

:doc:`documenteer.ext.remotecodeblock </sphinx-extensions/remote-code-block>`
   This extension allows you to include a literal code block where the source for that code block is available at an web URL.

:doc:`documenteer.ext.bibtex </sphinx-extensions/lsst-pybtex-style>`
   This extension works with the `sphinxcontrib-bibtex`_ extension to handle the BibTeX entires in https://github.com/lsst/lsst-texmf.

:doc:`documenteer.ext.githubbibcache </sphinx-extensions/githubbibcache>`
  This extension automatically downloads and caches the BibTeX files from https://github.com/lsst/lsst-texmf, for use with the `sphinxcontrib-bibtex`_ extension.

`myst_parser`_
   This extension allows you to use the MyST_ markup language (i.e., Markdown) in your technote.

`sphinx.ext.intersphinx`_
   This extension allows you to link to other Sphinx projects, including other Rubin technotes and user guides and many open-source projects like Astropy and Numpy.

`sphinxcontrib-bibtex`_
   This extension allow you to include a BibTeX-based bibliography in your technote.

`sphinx-prompt`_
   Sphinx-prompt lets you add a prompt to code blocks.
   This is useful for showing what a user might type at an interactive terminal.

`sphinxcontrib-mermaid`_
   Mermaid is a diagrams-as-code tool that allows you to create flowcharts, sequence diagrams, entity relationship diagrams, and more.
   See the Mermaid_ documentation for more information, and see the `sphinxcontrib-mermaid`_ documentation for Sphinx-specific usage.

`sphinx-diagrams`_
   The Diagrams extension allows you to make architectural diagrams from code.
   This extension is particularly useful for describing Kubernetes application deployments.

.. _technote-adding-extensions:

Adding additional extensions
============================

If you know of a Sphinx extension that you would like to use with your technote, you can add it yourself.
Here are the steps, using sphinxcontrib-mermaid_ as an example (this is already included in all technotes):

1. Add the extension's Python package to :file:`requirements.txt` in the technote's repository.
   This is the extension's PyPI package name, since technotes use pip to install build dependencies.

   .. code-block:: text
      :caption: requirements.txt
      :emphasize-lines: 2

      documenteer[technote]
      sphinxcontrib-mermaid

2. Add the extension to the :external+technote:ref:`technote.sphinx.extensions <toml-technote-sphinx-extensions>` array in :file:`technote.toml`.
   Either append to the existing array, or create a new array if it doesn't exist in the TOML file yet.

   .. code-block:: toml
      :caption: technote.toml
      :emphasize-lines: 2

      [technote.sphinx]
      extensions = ["sphinxcontrib.mermaid"]

   .. tip::

      The extension name is the Python package name, not the PyPI package name.
      Look at the extension's installation documentation for the ``extensions`` variable to find the Python package name.

   .. note::

      User-defined extensions are always installed *in addition to* the default extensions.
      You don't need to repeat the default extensions here.

3. If the extension has configurations, you can set those in the :file:`conf.py` file.

   .. code-block:: python
      :caption: conf.py
      :emphasize-lines: 3,4

      from documenteer.conf.technote import *  # noqa: F401, F403

      # -- Options for sphinxcontrib-mermaid -------------------------------------
      mermaid_version = "8.9.2"
