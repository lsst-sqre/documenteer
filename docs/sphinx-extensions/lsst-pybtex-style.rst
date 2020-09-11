.. default-domain:: rst

###############################
BibTeX style extension for LSST
###############################

`sphinxcontrib-bibtex <https://sphinxcontrib-bibtex.readthedocs.io/en/latest/index.html>`_ is an excellent way to include academic citations in Sphinx documentation projects.
Documenteer provides support for `LSST's common BibTeX bibliography files <https://github.com/lsst/lsst-texmf/tree/master/texmf/bibtex/bib>`__ (maintained in `lsst-texmf <https://github.com/lsst/lsst-texmf>`_) through its ``documenteer.sphinxext.bibtex`` extension.
Specifically, this extension provides support for ``docushare`` fields in those bib files.

To use this Sphinx extension, add ``documenteer.sphinxext.bibtex`` to your :file:`conf.py` file:

.. code-block:: python

   extensions = ["documenteer.sphinxext.bibtex"]

Usage
=====

In your reStructuredText file, declare a bibliography using the ``lsst_aa`` bibliography style:

.. code-block:: rst

   .. bibliography:: local.bib lsstbib/books.bib lsstbib/lsst.bib lsstbib/lsst-dm.bib lsstbib/refs.bib lsstbib/refs_ads.bib
      :style: lsst_aa

.. note::

   This arrangement of bib file is based on LSST technote projects, which :doc:`vendor the lsst-texmf bib files </technotes/refresh-lsst-bib>`.
   You will need to customize the bibliography file paths for your own usage.

Further reading
===============

- See `sphinxcontrib-bibtex's Usage documentaton <https://sphinxcontrib-bibtex.readthedocs.io/en/latest/usage.html#roles-and-directives>`_ to learn how to make citations in reStructuredText documents.
- For background on maintaining bib files in LSST technote projects, see :doc:`/technotes/refresh-lsst-bib`.
