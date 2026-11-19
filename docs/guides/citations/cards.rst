.. default-domain:: rst

.. _guide-citation-card:

##############
Citation cards
##############

The ``citation-card`` directive renders one of the site's citations as a card carrying the full citation, the citation's label, and its note.
It's the page-level counterpart to the :ref:`footer citations <guide-footer-citations>`, and suits a dedicated "Citing this site" page or a section of the home page.
Every card on this page is rendered from :ref:`this site's own citations <guide-citations>`.

.. directive:: .. citation-card:: [selector]

   Render one of the site's :ref:`[[project.citations]] <guide-project-citations>` entries as a card.
   The optional argument selects the entry by its :ref:`label <guide-project-citations-label>`, its :ref:`BibTeX key <guide-project-citations-bibtex-key>`, or its :ref:`DOI <guide-project-citations-doi>`.
   With no argument, the card renders the site's preferred citation.

   The card shows the citation's :ref:`label <guide-project-citations-label>`, the full bibliographic citation with the DOI as a ``https://doi.org/`` hyperlink, and the citation's :ref:`note <guide-project-citations-note>`.
   The card omits the note or the label when the entry doesn't set one.

   **Default: the site's preferred citation**

   With no argument, the card renders the site's :ref:`preferred <guide-project-citations-preferred>` citation: the work the site asks readers to cite.
   On a site that marks no entry ``preferred``, that's the entry marked :ref:`self = true <guide-project-citations-self>`:

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

   The citation ends in a link to the software's landing page rather than to doi.org, because the entry is located by a URL.
   The version is the one this build of the site documents (see :doc:`cff`).

   **Selecting a citation**

   The optional argument names the entry to render, so a page can also show a citation other than the preferred one:

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

   An entry can be selected by any of three names, matched exactly and case-sensitively: its :ref:`label <guide-project-citations-label>`, its :ref:`bibtex_key <guide-project-citations-bibtex-key>`, and its :ref:`DOI <guide-project-citations-doi>`.
   Each of these renders the same card for this site's paper:

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

   The DOI is also accepted as ``doi:10.26624/XWGH8202`` and as ``https://doi.org/10.26624/XWGH8202``, so a DOI copied from anywhere works.

   A label is a display string and :ref:`may repeat <guide-project-citations-label>`.
   The key and the DOI are unique site-wide, so use one of them when several entries share a label.
   An argument that matches two entries renders nothing and emits a warning that names both by key (see :ref:`guide-unresolvable-citations`).

   **Copying the BibTeX entry**

   Below the citation, the card carries a collapsed ``BibTeX`` disclosure holding the BibTeX entry composed from the same metadata, and a ``Copy BibTeX`` button that copies it to the clipboard.
   GitHub's "Cite this repository" button, Zenodo, and ADS all offer copying, and it matches how readers work: the entry goes into a :file:`.bib` file they already keep.
   A guide therefore never generates :file:`.bib` files of its own, and there's nothing to download.

   The entry type follows the citation's :ref:`type <guide-project-citations-type>`, so a copied entry says what the work is instead of filing everything under ``@misc``: ``type = "dataset"`` composes ``@dataset``, ``"article"`` composes ``@article``, ``"software"`` composes ``@software``, and ``"report"`` composes ``@techreport``.
   A citation typed ``"other"``, and one that declares no type at all, composes as ``@misc``.

   A ``@software`` or ``@dataset`` entry also carries a ``version`` field when the citation states a :ref:`version <guide-project-citations-version>`.
   Those are the two entry types that biblatex defines the field on, and the others omit it.
   The entry's *key* never carries the version, so a reader's :file:`.bib` file keeps working when the cited software is released again.

   **Citation keys**

   Every entry is keyed by something a reader already recognizes.
   The site's own work is keyed by the :file:`lsst.io` subdomain it's published at: a site at ``https://dp2.lsst.io`` composes ``@dataset{dp2,``, and the Software card above is keyed ``documenteer``.
   Every other work that has a DOI is keyed by the DOI, ``@misc{10.71929/rubin/3382528,``, which is how :file:`lsst.bib` keys its DataCite records.
   A work with neither falls back to author, year, and title (``jenness2022vera``).

   Those keys are stable: neither a subdomain nor a DOI changes when the site is rebuilt or released again, so a manuscript that copied an entry keeps citing the same key.
   A site that needs a particular key (the ``RTN-115`` an existing bibliography already uses, or the ADS bibcode a paper is indexed under) pins it with :ref:`bibtex_key <guide-project-citations-bibtex-key>`.
   This site pins its paper's key to its bibcode, which is why the Paper card above is keyed ``2025ASPC..541..151S`` rather than by its DOI:

   .. code-block:: toml

      [[project.citations]]
      doi = "10.26624/XWGH8202"
      bibtex_key = "2025ASPC..541..151S"

   See :ref:`bibtex_key <guide-project-citations-bibtex-key>` for the full rules, including what happens when two entries would take the same key.

   The BibTeX entry is part of the page's HTML rather than generated by a script, so it can always be selected and copied by hand.
   When a browser gives the page no clipboard access (on an insecure origin, for example), the button is removed and the entry stays.
   A page whose scripts never load keeps both.
   A non-HTML builder renders the entry as a plain literal block, since a disclosure and a button mean nothing there.

   An edit to ``[[project.citations]]`` reaches every card on the next build, which re-reads every page.
   See :ref:`guide-citation-rebuild`.

   **Options**

   ``class``
       Additional CSS classes to set on the card.

   ``name``
       A cross-reference target for the card.
