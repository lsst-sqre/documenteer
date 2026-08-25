.. default-domain:: rst

############################################
BibTeX style extension for Rubin Observatory
############################################

sphinxcontrib-bibtex_ is an excellent way to include academic citations in Sphinx documentation projects.
Documenteer provides support for `LSST's common BibTeX bibliography files <https://github.com/lsst/lsst-texmf/tree/main/texmf/bibtex/bib>`__ (maintained in `lsst-texmf <https://github.com/lsst/lsst-texmf>`__) through its ``documenteer.ext.bibtex`` extension.
Beyond the standard pybtex styles, the ``lsst_aa`` style:

- Supports the ``docushare`` field used in those bib files, rendering the handle as an ``ls.st`` link.
- Truncates author lists longer than seven names.
- Expands the journal and series name macros that ADS emits, such as ``\apj`` to ``ApJ``.
- Links Astrophysics Source Code Library records to ascl.net, using the ``archivePrefix`` field to tell an ASCL identifier apart from an arXiv one.
- Appends an ``[ADS]`` link to any entry with an ``adsurl`` field, which is often the only link available for conference proceedings.

Usage
=====

To use this Sphinx extension, add ``documenteer.ext.bibtex`` to your :file:`conf.py` file:

.. code-block:: python

   extensions = ["documenteer.ext.bibtex"]

   bibtex_default_style = "lsst_aa"

The ``bibtex_default_style`` configuration variable configures Sphinx.

Further reading
===============

- See `sphinxcontrib-bibtex's Usage documentation <https://sphinxcontrib-bibtex.readthedocs.io/en/latest/usage.html#roles-and-directives>`__ to learn how to make citations in reStructuredText documents.
- For using BibTeX files from the https://github.com/lsst/lsst-texmf repository, see :doc:`githubbibcache`.
