.. _technote-citations:

######################
Citing a technote
######################

A technote registered with a DOI is that DOI's *landing page*, and a landing page is expected to show the reader the DOI as a resolvable ``https://doi.org/`` link together with a complete bibliographic record.
A technote does that in two places — a citation at the end of the article, and a **Cite** section in the sidebar — and states the same identity again in metadata a harvester can read.
Everything follows from the DOI in :file:`technote.toml`:

.. code-block:: toml
   :caption: technote.toml

   [technote]
   id = "SQR-000"
   doi = "10.71929/rubin/2570308"
   canonical_url = "https://sqr-000.lsst.io/"

   [technote.organization]
   name = "Vera C. Rubin Observatory"

A technote that sets no ``doi`` shows no citation surfaces — not an empty section — so its pages look as they did.
Its ``<head>`` metadata is another matter.
technote 0.11, which Documenteer now requires, adds a Dublin Core block and a schema.org ``Report`` node to every technote, DOI or not, and renames the Highwire tag ``citation_date`` to ``citation_publication_date``; anything that scrapes the old name needs updating.
See the :doc:`changelog </changelog>` entry for that requirement and the `technote 0.11 release notes <https://technote.lsst.io/changelog.html>`__.

Citing this document
====================

The article ends with a **Citing this document** section: the complete citation, in the display form DataCite recommends, with the DOI written as a resolvable hyperlink.

.. code-block:: text
   :caption: Rendered at the end of the article

   Sick, Jonathan (2026). The LSST DM Technical Note Publishing Platform.
   Vera C. Rubin Observatory. https://doi.org/10.71929/rubin/2570308

The creators are the ``[[technote.authors]]`` entries, in order and family name first; the publisher is ``technote.organization.name``, and the year is the year of the technote's ``date_updated`` — the date :file:`technote.toml` declares, or, where it declares none, the date of the commit the technote is published from; see :ref:`technote-citation-date` below.
This is the sentence a reader copies into a bibliography, so it is composed from the technote's own metadata during the build and can never disagree with the page it sits at the end of.

The Cite section
================

The sidebar's **Cite** section shows the DOI as a full ``https://doi.org/`` hyperlink, and offers the technote's BibTeX entry behind a **BibTeX** disclosure with a button that copies it to the clipboard.

The entry is composed during the build from the technote's own metadata, so it never disagrees with the page it sits on:

.. code-block:: bibtex

   @techreport{SQR-000,
       author = {Sick, Jonathan},
       title = {{The LSST DM Technical Note Publishing Platform}},
       year = {2026},
       month = {March},
       institution = {Vera C. Rubin Observatory},
       number = {SQR-000},
       doi = {10.71929/rubin/2570308},
       url = {https://sqr-000.lsst.io/}
   }

A technote is a technical report, so the entry is a BibTeX ``techreport``: the publishing organization is its ``institution`` and the technote's handle is its ``number``.
The ``year`` and ``month`` are those of the technote's ``date_updated``; the year is the same one the citation at the end of the article shows.

The citation key is the handle as well, written exactly as ``id`` in :file:`technote.toml` spells it.
That is how Rubin authors already cite technotes: lsst-texmf's :file:`lsst.bib` keys every technote and document entry by handle, so ``\citeds{SQR-000}`` in an lsstdoc document and ``\cite{SQR-000}`` against this entry resolve the same key.
It also means the key never moves — a technote can be retitled, re-authored, or re-dated, and a bibliography that already stores the entry keeps working.
A technote outside a series, with no ``id`` to key by, falls back to a key composed from the first author, the year, and the first word of the title.

The entry is written into the page rather than fetched, so a reader can select and copy it by hand on a page whose JavaScript never runs.
Where the browser offers no clipboard API, the copy button removes itself instead of failing silently when pressed.

.. _technote-citation-date:

Where the date comes from
=========================

A technote's citation is dated by ``[technote] date_updated``:

.. code-block:: toml
   :caption: technote.toml

   [technote]
   date_updated = 2026-03-04

A technote that declares none is dated by the commit it is published from — the committer date of the commit the build checked out, which for a technote published by CI is the push that published it.
``SOURCE_DATE_EPOCH`` takes precedence over the commit where a reproducible-build wrapper sets one, and the build clock is used only outside a Git repository, where there is no commit to read.
``date_created`` is never consulted: it is the day the technote was *started*, which is neither the day it was published nor the day it was last revised.

Either way the technote has exactly one date, and every surface states that one: the sidebar's **Updated** line, the ``citation_publication_date`` metadata tag, the JSON-LD block, the **Cite** section, and the citation at the end of the article.
Rebuilding an unchanged commit composes exactly the same citation, so a reader who has already stored the BibTeX entry keeps a working one.

Declaring ``date_updated`` is how you *pin* the date.
Without it the citation follows the latest commit, so a typo fix re-dates the work; with it the citation states the day you chose and goes on stating it however often the repository is touched afterwards.
That is the field to set for a technote whose publication date is a fact about the document rather than about its repository — a version released on a particular day, or a document whose DOI was minted for a particular text.

The same date is what :command:`documenteer technote sync-cff` writes as ``date-released``, with one deliberate difference: it writes the field only from a *declared* ``date_updated``, never from the commit date.
See :doc:`citation-file` for why.

Metadata for harvesters
=======================

The page's ``<head>`` states the same identity for software that reads it rather than for a person:

- ``citation_doi``, the `Highwire <https://scholar.google.com/intl/en/scholar/inclusion.html>`__ tag Google Scholar reads, with the bare DOI.
- ``DC.identifier``, the Dublin Core tag repository software reads, with the DOI as a ``https://doi.org/`` URL.
- A `schema.org <https://schema.org/Report>`__ JSON-LD block describing the technote as a ``Report``, with the DOI as both the node's ``@id`` and its ``identifier``, following the DataCite-to-schema.org crosswalk.

These come from the same ``doi`` field, so nothing has to be kept in step by hand.

Keeping :file:`CITATION.cff` in step
====================================

The same metadata also feeds the :file:`CITATION.cff` file behind GitHub's "Cite this repository" button:

.. prompt:: bash

   documenteer technote sync-cff

The file is fully generated, so keeping the two in step is a matter of running :command:`documenteer technote sync-cff --check` in CI, where the technote is built anyway; it fails the build with the command to run, and Rubin's shared technote workflow runs it for you.
See :doc:`citation-file` for what the file contains and how that check behaves.

.. seealso::

   :ref:`guide-citations` covers the same surfaces for a user guide, which declares its citations in :file:`documenteer.toml` instead.
