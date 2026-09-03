.. _technote-citations:

######################
Citing a technote
######################

A technote registered with a DOI is that DOI's *landing page*, and a landing page is expected to show the reader the DOI as a resolvable ``https://doi.org/`` link together with a complete bibliographic record.
A technote does that in its sidebar, from the DOI in :file:`technote.toml`:

.. code-block:: toml
   :caption: technote.toml

   [technote]
   id = "SQR-000"
   doi = "10.71929/rubin/2570308"
   canonical_url = "https://sqr-000.lsst.io/"

   [technote.organization]
   name = "Vera C. Rubin Observatory"

A technote that sets no ``doi`` shows no citation at all — not an empty section — so most technotes are unaffected.

.. seealso::

   :doc:`citation-file` generates a :file:`CITATION.cff` from the same metadata, which is what GitHub's "Cite this repository" button reads.

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
The year is the date the technote was last updated, matching the date the sidebar shows, and falls back to the date it was created.

The entry is written into the page rather than fetched, so a reader can select and copy it by hand on a page whose JavaScript never runs.
Where the browser offers no clipboard API, the copy button removes itself instead of failing silently when pressed.

.. seealso::

   :ref:`guide-citations` covers the same surfaces for a user guide, which declares its citations in :file:`documenteer.toml` instead.
