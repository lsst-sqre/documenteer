#################################
Sourcing BibTeX files from GitHub
#################################

For documentation that references published documents, it's useful formally cite references in additional to the typical practice of linking directly to other webpages.
In the Sphinx documentation system, a good workflow is to code bibliographic references through standard BibTeX files and then reference items in those BibTeX files with the sphinxcontrib-bibtex_ extension.
At Rubin Observatory, we maintain a centralized set of BibTeX files in the https://github.com/lsst/lsst-texmf  repository.
Documenteer provides a Sphinx extension, ``documenteer.ext.githubbibcache``, that downloads BibTeX files from one or more GitHub repositories, caches them, and automatically configures sphinxcontrib-bibtex_ to use those BibTeX files.
This page explains how to set up ``documenteer.ext.githubbibcache`` in your Sphinx documentation project and use it in conjunction with the sphinxcontrib-bibtex_ extension.

.. tip::

   If you're using one of the Documenteer configuration presets for Rubin Observatory documents, your Sphinx project is already configured to use https://github.com/lsst/lsst-texmf bibliography files.
   All you need to do is use the sphinxcontrib-bibtex_ extension's citation roles and ensure that a bibliography directive is present in your documentation project.

Extension set up
================

The extension from Documenteer needs to be loaded _before_ the sphinxcontrib-bibtex_ extension because it adds configurations that are later used by sphinxcontrib-bibtex_.
In your project's :file:`conf.py` file, set up the extensions like this:

.. code-block:: python
   :caption: conf.py

   extensions = [
       "documenteer.ext.githubbibcache",
       "sphinxcontrib.bibtex",
   ]

.. note::

   If you're using BibTeX files from https://github.com/lsst/lsst-texmf, you'll need to set also add an extension that supports Rubin Observatory's custom ``@DocuShare`` BibTeX entry type through :doc:`lsst-pybtex-style`.
   This configuration is then:

   .. code-block:: python
      :caption: conf.py

      extensions = [
          "documenteer.ext.bibtex",
          "documenteer.ext.githubbibcache",
          "sphinxcontrib.bibtex",
      ]

      bibtex_default_style = "lsst_aa"

   The style configuration specifies the style provided by ``documenteer.ext.bibtex``.

Specify the GitHub repositories and their BibTeX files
======================================================

In :file:`conf.py`, you'll need to specify the GitHub repositories and their BibTeX files that you want to use.
The ``documenteer_bibfile_github_repos`` variable is a list of dictionaries, where each dictionary has the following keys:

- ``repo``: the GitHub repository name, e.g., ``lsst/lsst-texmf``.
- ``ref``: the Git reference (branch, tag, or commit hash) to use, e.g., ``main``.
- ``bibfiles``: a list of paths to BibTeX files to download from the repository, e.g., ``['texmf/bibtex/bib/refs.bib', 'texmf/bibtex/bib/lsst.bib']``.

This is a sample configuration used in by Rubin Observatory's :doc:`technote configuration </technotes/index>`:

.. code-block:: python
   :caption: conf.py

   documenteer_bibfile_cache_dir = ".technote/bibfiles"
   documenteer_bibfile_github_repos = [
       {
           "repo": "lsst/lsst-texmf",
           "ref": "main",
           "bibfiles": [
               "texmf/bibtex/bib/lsst.bib",
               "texmf/bibtex/bib/lsst-dm.bib",
               "texmf/bibtex/bib/refs_ads.bib",
               "texmf/bibtex/bib/refs.bib",
               "texmf/bibtex/bib/books.bib",
           ],
       }
   ]
   # Set up bibtex_bibfiles
   bibtex_bibfiles = []

   # Automatically load local bibfiles in the root directory.
   for p in Path.cwd().glob("*.bib"):
       bibtex_bibfiles.append(str(p))

   bibtex_default_style = "lsst_aa"
   bibtex_reference_style = "author_year"

Create a bibliography and make citations
========================================

The extension, ``documenteer.ext.githubbibcache``, configures sphinxcontrib-bibtex_ to use the specified BibTeX files from GitHub.
Now you can use sphinxcontrib-bibtex_ as normal in your documentation project.

First, ensure there's a ``bibliography`` directive in your documentation project:

.. code-block:: rst
   :caption: index.rst

   References
   ==========

   .. bibliography::

Then, you can use the citation roles provided by sphinxcontrib-bibtex_.

Regular citations are made with the :rst:role:`cite` role, and textual citations are made with the :rst:role:`cite:t` role:

.. code-block:: rst
   :caption: index.rst

   Rubin Observatory is a large astronomical survey telescope that will be
   used to study the Universe :cite:`2019ApJ...873..111I`.

   The Science Book :cite:t:`2009arXiv0912.0201L` describes the science goals
   of Rubin Observatory.

Clearing the BibTeX cache
=========================

By default, the extension caches the BibTeX files in a directory called :file:`_build/bibfile-cache` relative to your project's :file:`conf.py` file.
You can also customize this directory by setting the ``documenteer_bibfile_cache_dir`` variable in :file:`conf.py`.
For example, Documenteer's technote configuration sets this variable to ``.technote/bibfiles``.
To get new copies of the bibtex files from GitHub, you can delete the cache directory and rebuild your documentation project.
