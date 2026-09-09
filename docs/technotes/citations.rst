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

A technote that sets no ``doi`` shows no citation at all — not an empty section — so most technotes are unaffected.

Citing this document
====================

The article ends with a **Citing this document** section: the complete citation, in the display form DataCite recommends, with the DOI written as a resolvable hyperlink.

.. code-block:: text
   :caption: Rendered at the end of the article

   Sick, Jonathan (2026). The LSST DM Technical Note Publishing Platform.
   Vera C. Rubin Observatory. https://doi.org/10.71929/rubin/2570308

The creators are the ``[[technote.authors]]`` entries, in order and family name first; the publisher is ``technote.organization.name``, and the year is the year of the ``date_updated`` :file:`technote.toml` declares.
A technote that declares no ``date_updated`` is cited undated — the ``(YYYY)`` is dropped rather than guessed at — and the build says so; see :ref:`technote-undated-citations` below.
This is the sentence a reader copies into a bibliography, so it is composed from the technote's own metadata during the build and can never disagree with the page it sits at the end of.

The Cite section
================

The sidebar's **Cite** section shows the DOI as a full ``https://doi.org/`` hyperlink, and offers the technote's BibTeX entry behind a **BibTeX** disclosure with a button that copies it to the clipboard.

The entry is composed during the build from the technote's own metadata, so it never disagrees with the page it sits on:

.. code-block:: bibtex

   @techreport{sick2026the,
       author = {Sick, Jonathan},
       title = {{The LSST DM Technical Note Publishing Platform}},
       year = {2026},
       institution = {Vera C. Rubin Observatory},
       number = {SQR-000},
       doi = {10.71929/rubin/2570308},
       url = {https://sqr-000.lsst.io/}
   }

A technote is a technical report, so the entry is a BibTeX ``techreport``: the publishing organization is its ``institution`` and the technote's handle is its ``number``.
The ``year`` is the year of the declared ``date_updated``, the same year the citation at the end of the article shows.

The entry is written into the page rather than fetched, so a reader can select and copy it by hand on a page whose JavaScript never runs.
Where the browser offers no clipboard API, the copy button removes itself instead of failing silently when pressed.

.. _technote-undated-citations:

Technotes with no date
======================

Only a ``date_updated`` written in :file:`technote.toml` dates a technote's citation:

.. code-block:: toml
   :caption: technote.toml

   [technote]
   date_updated = 2026-03-04

``date_created`` is not read as a fallback, because it is the day the technote was started — neither the day it was published nor the day it was last revised.
Nor is the date the technote's own metadata carries: the ``technote`` package fills that in with the time of the build whenever :file:`technote.toml` omits the field, so reading it would date the citation to the day the technote was last built, re-dating it on every rebuild and disagreeing with the deliberately undated :file:`CITATION.cff` written from the same file.

A technote that declares no ``date_updated`` is therefore cited undated wherever it is cited: the displayed citation loses its ``(YYYY)``, the BibTeX entry carries no ``year`` field, and its key is built from the author and title alone.
Nothing on the rendered page says so, so the build does, once, naming the field to set:

.. code-block:: text

   WARNING: this technote's citation states no publication date, so it is
   displayed without its year, its BibTeX entry carries no year field, and its
   BibTeX key is built without one. Set date_updated in the [technote] table in
   technote.toml. [documenteer.citation_date]

A ``-W`` build fails on it, so a technote with no date to give silences it by name:

.. code-block:: python

   # conf.py
   suppress_warnings = ["documenteer.citation_date"]

Rendering is unchanged either way, and a technote that declares no ``doi`` shows no citation at all and is never reported.

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
