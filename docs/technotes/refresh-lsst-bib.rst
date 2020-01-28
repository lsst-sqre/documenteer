#####################################################
Maintaining common BibTeX files with refresh-lsst-bib
#####################################################

Sphinx technotes *vendor* `LSST's common BibTeX bibliography files <https://github.com/lsst/lsst-texmf/tree/master/texmf/bibtex/bib>`__ (maintained in `lsst-texmf <https://github.com/lsst/lsst-texmf>`_) into an :file:`lsstbib` directory, contained within the technote's repository.
These bib files are checked into a technote's Git repository so that the technote is repeatably buildable independently of lsst-texmf, and without resorting to complicated techniques like Git submodules.

Periodically you may need to update these bib files with the latest versions available from the lsst-texmf repository.
Documenteer includes the :ref:`refresh-lsst-bib <refresh-lsst-bib-ref>`, also available through technote's ``make refresh-bib`` target, to make this process straightforward.

Steps for updating LSST BibTeX files
====================================

1. From the root directory of the technote, run:

   .. prompt:: bash

      make refresh-bib

   This command runs :ref:`refresh-lsst-bib <refresh-lsst-bib-ref>` and downloads the latest bib files from lsst-texmf's ``master`` branch on GitHub.

2. Commit the modified bib files:

   .. prompt:: bash

      git add lsstbib/*.bib
      git commit

.. _refresh-lsst-bib-ref:

Command reference
=================

.. autoprogram:: documenteer.bin.refreshlsstbib:make_parser()
