.. default-domain:: rst

.. _guide-citation-card:

##############
Citation cards
##############

The ``citation-card`` directive renders one of the site's citations as a card carrying the full citation, the citation's label, and its note.
It is the page-level counterpart to the :ref:`footer citations <guide-footer-citations>`, and is the right tool for a dedicated "Citing this site" page, or for a section of the home page.
Every card on this page is rendered from :ref:`this site's own citations <guide-citations>`.

.. directive:: .. citation-card:: [selector]

   Render one of the site's :ref:`[[project.citations]] <guide-project-citations>` entries as a card.
   The optional argument selects the entry by its label, its BibTeX key, or its DOI; with no argument the card renders the site's preferred citation.

   The card shows the citation's :ref:`label <guide-project-citations-label>`, the full bibliographic citation with the DOI as a ``https://doi.org/`` hyperlink, and the citation's :ref:`note <guide-project-citations-note>`.
   An entry that sets no note renders no note, and an entry with no label renders no label.

   **Default: the site's preferred citation**

   With no argument, the card renders the site's :ref:`preferred <guide-project-citations-preferred>` citation — the work the site asks readers to cite, which is the entry marked :ref:`self = true <guide-project-citations-self>` on a site that marks no other:

   .. tab-set::

      .. tab-item:: reStructuredText
         :sync: rst

         .. code-block:: rst

            .. citation-card::

      .. tab-item:: markdown
         :sync: md

         .. code-block:: markdown

            :::{citation-card}
            :::

   On this site the preferred citation is Documenteer itself, read from the repository's :file:`CITATION.cff` file, so that card renders as:

   .. citation-card::

   The citation ends in a link to the software's landing page rather than to doi.org, because the entry is located by a URL; the version is the one this build of the site documents (see :doc:`cff`).

   **Selecting a citation**

   The optional argument names the entry to render, so a page can also show a citation that isn't the site's own:

   .. tab-set::

      .. tab-item:: reStructuredText
         :sync: rst

         .. code-block:: rst

            .. citation-card:: Paper

      .. tab-item:: markdown
         :sync: md

         .. code-block:: markdown

            :::{citation-card} Paper
            :::

   An entry answers to three names, matched exactly and case-sensitively: its :ref:`label <guide-project-citations-label>`, its :ref:`bibtex_key <guide-project-citations-bibtex-key>`, and its DOI.
   Each of these renders the same card of this site's paper:

   .. tab-set::

      .. tab-item:: By label

         .. code-block:: rst

            .. citation-card:: Paper

         .. citation-card:: Paper

      .. tab-item:: By BibTeX key

         .. code-block:: rst

            .. citation-card:: 2025ASPC..541..151S

         .. citation-card:: 2025ASPC..541..151S

      .. tab-item:: By DOI

         .. code-block:: rst

            .. citation-card:: 10.26624/XWGH8202

         .. citation-card:: 10.26624/XWGH8202

   The DOI is also accepted as ``doi:10.26624/XWGH8202`` and as ``https://doi.org/10.26624/XWGH8202``, so a DOI copied from anywhere selects.

   A label is a display string and :ref:`may repeat <guide-project-citations-label>`; the key and the DOI are unique site-wide, and are what a page selects with when several entries share a heading.
   An argument two entries answer to renders nothing and warns, naming both by key (see :ref:`guide-unresolvable-citations`).

   **Copying the BibTeX entry**

   Below the citation, the card carries a collapsed ``BibTeX`` disclosure holding the entry composed from the same metadata, and a ``Copy BibTeX`` button that puts it on the clipboard.
   Copying is what GitHub's "Cite this repository", Zenodo, and ADS all offer, and it is what a reader wants: the entry goes into a :file:`.bib` file they already keep.
   A guide therefore never generates :file:`.bib` files of its own, and there is nothing to download.

   The entry type follows the citation's :ref:`type <guide-project-citations-type>`, so a copied entry says what the work is instead of filing everything under ``@misc``: ``type = "dataset"`` composes ``@dataset``, ``"article"`` composes ``@article``, ``"software"`` composes ``@software``, and ``"report"`` composes ``@techreport``.
   A citation typed ``"other"``, and one that declares no type at all, composes as ``@misc``.

   A ``@software`` or ``@dataset`` entry also carries a ``version`` field when the citation states a :ref:`version <guide-project-citations-version>` — those are the two entry types biblatex defines the field on, and the others omit it.
   The entry's *key* never carries the version, so a reader's :file:`.bib` file keeps working when the cited software is released again.

   **Citation keys**

   Every entry is keyed by something a reader already recognizes.
   The site's own work is keyed by the :file:`lsst.io` subdomain it is published at — a site at ``https://dp2.lsst.io`` composes ``@dataset{dp2,``, and the Software card above is keyed ``documenteer`` — and every other work that has a DOI is keyed by the DOI, ``@misc{10.71929/rubin/3382528,``, which is how :file:`lsst.bib` keys its DataCite records.
   A work with neither falls back to author, year, and title (``jenness2022vera``).

   Those keys are stable: neither a subdomain nor a DOI changes when the site is rebuilt or released again, so a manuscript that copied an entry keeps citing the same key.
   A site that needs a particular key — the ``RTN-115`` an existing bibliography already uses, or the ADS bibcode a paper is indexed under — pins it.
   This site pins its paper's key to its bibcode, which is why the Paper card above is keyed ``2025ASPC..541..151S`` rather than by its DOI:

   .. code-block:: toml

      [[project.citations]]
      doi = "10.26624/XWGH8202"
      bibtex_key = "2025ASPC..541..151S"

   See :ref:`bibtex_key <guide-project-citations-bibtex-key>` for the full rules, including what happens when two entries would take the same key.

   The entry is in the page rather than in a script, so it can always be selected and copied by hand.
   A browser that gives the page no clipboard access — an insecure origin, say — has the button removed and keeps the entry; a page whose scripts never load keeps both.
   A non-HTML builder renders the entry as a plain literal block, since a disclosure and a button mean nothing there.

   An edit to ``[[project.citations]]`` reaches every card on the next build, which re-reads every page; see :ref:`guide-citation-rebuild`.

   **Options**

   ``class``
       Additional CSS classes to set on the card.

   ``name``
       A cross-reference target for the card.
