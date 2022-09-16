#########################
Rubin user guide features
#########################

Documenteer provides a configuration preset for Rubin Observatory documentation sites built with Sphinx.
This page provides an overview of the preset's features.

If you want to get started using the configuration preset right away, see :doc:`configuration`.

Based on the PyData Sphinx Theme
================================

The base theme for Rubin user guides is `PyData Sphinx Theme`_, a responsive design built around a three-pane layout with both light and dark color pallets.
The Rubin user guide preset brands and configures the PyData theme, so that colors, logos, typefaces, and other design features are ready to go.
For advice on how to structure your user guide's content to work with the PyData Sphinx Theme's navigation structure, see :doc:`organization`.

Besides the design features of `PyData Sphinx Theme`_ itself, the Rubin user guide preset also includes the `Sphinx Design`_ extension, which provides useful design features like tab sets and badges.
See the `Sphinx Design`_ docs and the :ref:`toc-guides-design` pages in these docs for ideas.

Configuration with documenteer.toml
===================================

The Rubin user guide preset is configurable through a TOML_ file, :doc:`documenteer.toml <toml-reference>`, which reduces the amount of overriding necessary in the standard Sphinx :file:`conf.py` file.
See :doc:`configuration` to get started.

Python projects that use the standard :file:`pyproject.toml` metadata file for packaging benefit from automatic metadata introspection.
See :doc:`pyproject-configuration` and :ref:`toc-guides-advanced-config` pages for details.

Markdown support
================

Rubin user guides can be written in Markdown, in addition to reStructuredText, thanks to the MyST_ extension.
Through MyST_, reStructuredText/Sphinx directives and roles are available as a layer on top of standard Markdown syntax.
See the MyST_ documentation for more details on how to use reStructuredText features from Markdown.

Diagrams as code
================

Support for Mermaid_ is built in, enabling you to add standard technical diagrams with restoring to graphics editors or binary files
For infrastructure diagrams, we recommend using Diagrams_, which you can easily install and configure.

See :doc:`diagrams` for more information.

Python APIs with automodapi and autodoc
=======================================

The Rubin user guide preset configures a suite of Sphinx extensions for generating Python reference documentation from docstrings:

- autodoc_
- napoleon_
- sphinx_autodoc_typehints_
- automodapi_
