.. default-domain:: rst

.. _guide-citations:

#########
Citations
#########

A site that is published with a DOI is that DOI's *landing page*, and a landing page is expected to show the reader a complete bibliographic citation with the DOI written as a resolvable ``https://doi.org/`` link.
A guide displays its citations in three places:

- The :ref:`site footer <guide-footer-citations>`, on every page.
- A :ref:`citation card <guide-citation-card>`, wherever a page asks for one.
- An :ref:`inline DOI link <guide-citation-doi-role>`, wherever a sentence, a bullet, or a table cell refers to one of the works.

All three read the same citations, so they can never disagree about what the site asks to be cited as.

Declaring the citations
=======================

Every one of those surfaces renders the citations the site declares in the :ref:`[[project.citations]] <guide-project-citations>` array of :file:`documenteer.toml`; none carries bibliographic fields of its own.
A site that documents a data release typically declares two citations — the release itself, which this site is the landing page for, and the paper that describes it:

.. code-block:: toml

   # documenteer.toml

   [[project.citations]]
   doi = "10.71929/rubin/2570308"
   label = "Dataset"
   type = "dataset"
   self = true
   note = "To be used when citing the DP2 dataset and this documentation."
   title = "Data Preview 2"
   publisher = "Vera C. Rubin Observatory"
   date = 2025-06-30
   authors = [{ name = "Vera C. Rubin Observatory" }]

   [[project.citations]]
   doi = "10.5281/zenodo.1234567"
   label = "Paper"
   type = "article"
   title = "The Data Preview 2 release"
   publisher = "Zenodo"
   date = 2025-06-30
   authors = [{ name = "Vera C. Rubin Observatory" }]

Two of the fields there answer two different questions, and it is worth keeping them apart:

:ref:`self <guide-project-citations-self>`
    Whether this site is the DOI's registered *landing page* — whether doi.org sends a reader here.
    It alone drives the machine-readable metadata in each page's ``<head>``.

:ref:`preferred <guide-project-citations-preferred>`
    Which citation the site asks readers to *use*.
    It is what a card with no argument renders.

They coincide above, and a site that publishes its own DOI never needs to think about the difference: an entry marked ``self`` is the preferred citation unless another entry claims that.

They part ways for a site whose citation is a work published somewhere else — a software repository whose :file:`CITATION.cff` prefers the paper that describes it, say.
That paper's landing page is its publisher's, so the site marks it ``preferred`` and marks nothing ``self``:

.. code-block:: toml

   # documenteer.toml

   [[project.citations]]
   cff = "../CITATION.cff"
   label = "Paper"
   preferred = true
   note = "Cite this paper in publications that use the package."

The site then displays that citation everywhere it displays one, while no page of it claims to be the paper's landing page.
Setting :ref:`self <guide-project-citations-self>` on that entry instead is an error the build reports, since it would publish every page of the site as the paper's full text — a claim only the paper's publisher can make.

Such a repository is often worth citing twice — the paper for the work, and the package for the code that was run.
A second entry against the same file, with :ref:`cff_preferred = false <guide-project-citations-cff-preferred>`, reads the file's top-level record rather than its preferred citation:

.. code-block:: toml

   # documenteer.toml

   [[project.citations]]
   cff = "../CITATION.cff"
   cff_preferred = false
   label = "Software"
   in_footer = true
   note = "Cite the version you ran; this page names the version it documents."

A package that has never been deposited for a DOI is cited by where it lives: the file's ``url``, or its ``repository-code`` when it names no landing page.
The entry states no :ref:`type <guide-project-citations-type>` either, and does not need to: a top-level record that declares none is read as ``software``, the default CFF defines for that key, so the citation composes as ``@software`` and publishes as a `SoftwareSourceCode <https://schema.org/SoftwareSourceCode>`__.
Only the :ref:`self <guide-project-citations-self>` entry needs a DOI, because that entry is the claim that this site is a DOI's landing page.

It states no :ref:`version <guide-project-citations-version>` either, and gets one anyway.
An entry reading a repository's own record describes this site's own package, so it takes the file's ``version`` when the file states one and the site's own :ref:`project.version <guide-project-version>` otherwise.
Against a :file:`CITATION.cff` for ``safir``, released in 2020 and documented at 12.3.0, the entry renders:

.. code-block:: text

   SOFTWARE

   Vera C. Rubin Observatory (2020). Safir (version 12.3.0).
   https://github.com/lsst-sqre/safir

   Cite the version you ran; this page names the version it documents.

That release is what a software citation exists to carry, which is why the note is written around it rather than around the year.
Software released continuously has no publication date to speak of.
Its :ref:`date <guide-project-citations-date>` is conventionally the year of its first release, which is defensible precisely because it never moves — every later release cites the same way, so a reader's bibliography does not churn — but it is not what identifies the code that ran.
The version is.
That is also why an entry like this one — software located by its repository, stating no date — is not reported as :ref:`undated <guide-undated-citations>`.

A site can also set ``self`` and ``preferred`` on *different* entries, which is the site published with a DOI of its own that nonetheless asks readers to cite something else.
The :ref:`footer <guide-footer-citations>` then shows both by default, because a landing page owes its reader the citation of the DOI it is the landing page of whether or not that is the citation it asks for.
Such a site shows one of them instead by writing :ref:`in_footer = false <guide-project-citations-in-footer>` on the other.

.. _guide-citation-card:

Citation cards
==============

The ``citation-card`` directive renders one of the site's citations as a card carrying the full citation, the citation's label, and its note.
It is the page-level counterpart to the footer citations, and is the right tool for a dedicated "Citing this site" page, or for a section of the home page.

.. directive:: .. citation-card:: [label]

   Render one of the site's :ref:`[[project.citations]] <guide-project-citations>` entries as a card.

   The card shows the citation's :ref:`label <guide-project-citations-label>`, the full bibliographic citation with the DOI as a ``https://doi.org/`` hyperlink, and the citation's :ref:`note <guide-project-citations-note>`.
   An entry that sets no note renders no note, and an entry with no label renders no label.

   **Default: the site's own citation**

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

   With the configuration above, that card reads:

   .. code-block:: text

      DATASET

      Vera C. Rubin Observatory (2025). Data Preview 2. Vera C. Rubin
      Observatory. https://doi.org/10.71929/rubin/2570308

      To be used when citing the DP2 dataset and this documentation.

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

   An entry answers to three names, matched exactly and case-sensitively:

   .. code-block:: rst

      .. citation-card:: Paper
      .. citation-card:: RTN-115
      .. citation-card:: 10.71929/rubin/3382540

   ``Paper`` is the entry's :ref:`label <guide-project-citations-label>`, ``RTN-115`` its :ref:`bibtex_key <guide-project-citations-bibtex-key>`, and the last its DOI — which is also accepted as ``doi:10.71929/rubin/3382540`` and as ``https://doi.org/10.71929/rubin/3382540``, so a DOI copied from anywhere selects.

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
   The site's own work is keyed by the :file:`lsst.io` subdomain it is published at — a site at ``https://dp2.lsst.io`` composes ``@dataset{dp2,`` — and every other work that has a DOI is keyed by the DOI, ``@misc{10.71929/rubin/3382528,``, which is how :file:`lsst.bib` keys its DataCite records.
   A work with neither falls back to author, year, and title (``jenness2022vera``).

   Those keys are stable: neither a subdomain nor a DOI changes when the site is rebuilt or released again, so a manuscript that copied an entry keeps citing the same key.
   A site that needs a particular key — the ``RTN-115`` an existing bibliography already uses, say — pins it:

   .. code-block:: toml

      [[project.citations]]
      doi = "10.71929/rubin/2570308"
      bibtex_key = "RTN-115"

   See :ref:`bibtex_key <guide-project-citations-bibtex-key>` for the full rules, including what happens when two entries would take the same key.

   The entry is in the page rather than in a script, so it can always be selected and copied by hand.
   A browser that gives the page no clipboard access — an insecure origin, say — has the button removed and keeps the entry; a page whose scripts never load keeps both.
   A non-HTML builder renders the entry as a plain literal block, since a disclosure and a button mean nothing there.

   **Options**

   ``class``
       Additional CSS classes to set on the card.

   ``name``
       A cross-reference target for the card.

.. _guide-citation-doi-role:

Inline DOI links
================

A card is a block, so a page that only needs to *mention* a work — the first bullet of an access list, a cell in a table of data products, a sentence pointing at the paper — cannot use one.
The ``doi`` role links a declared citation's DOI inline instead, reading the same :ref:`[[project.citations]] <guide-project-citations>` entries the card and the footer do.
A page that would otherwise write ``https://doi.org/10.71929/rubin/3382539`` into a sentence by hand, or into a substitution that holds it, names the entry's label and gets whatever the configuration declares.

.. role:: doi

   Link one of the site's :ref:`[[project.citations]] <guide-project-citations>` entries by its DOI.

   The role's content names the entry, resolved the same way the :ref:`citation-card <guide-citation-card>` directive's argument is: by :ref:`label <guide-project-citations-label>`, by :ref:`bibtex_key <guide-project-citations-bibtex-key>`, or by DOI in any spelling, matched exactly and case-sensitively.
   The link's text is the resolvable ``https://doi.org/`` URL, the form the Crossref and DataCite display guidelines ask for:

   .. tab-set::

      .. tab-item:: reStructuredText
         :sync: rst

         .. code-block:: rst

            The catalog is published as :doi:`Object catalog`.

      .. tab-item:: markdown
         :sync: md

         .. code-block:: markdown

            The catalog is published as {doi}`Object catalog`.

   **Custom link text**

   The standard ``text <target>`` spelling puts your own words on the link, for a sentence that should read as prose rather than as an identifier:

   .. tab-set::

      .. tab-item:: reStructuredText
         :sync: rst

         .. code-block:: rst

            For processing details see :doi:`the DP2 paper <Paper>`.

      .. tab-item:: markdown
         :sync: md

         .. code-block:: markdown

            For processing details see {doi}`the DP2 paper <Paper>`.

   It is also what lets a sentence display one word over an entry it selects unambiguously, which is how a site whose products all need the word "TAP" writes them:

   .. code-block:: rst

      * TAP: :doi:`TAP <10.71929/rubin/3382540>`

   **Where it works**

   The role renders one external hyperlink and nothing else, so it composes wherever inline markup does: a sentence, a list item, a table cell, and the body of a ``replace`` substitution definition.
   A data product's "Access" list is the case it was added for:

   .. code-block:: rst

      Access
      ------

      * DOI: :doi:`Object catalog`
      * TAP table name: ``dp02_dc2_catalogs.Object``

   .. code-block:: rst

      .. |dp2_paper| replace:: :doi:`the DP2 paper <Paper>`

   There is no default entry: the role always names one.
   A role appears mid-sentence, where an implicit subject would be a guess at which of the site's works the sentence is about.

The role is a link, and only a link — no note, no BibTeX entry, no author-year text.
A page that *is* a work's landing page should therefore carry a :ref:`card <guide-citation-card>` for it and use the role only for short references elsewhere, since the card is what shows a reader the full citation and the entry they came for.

Citing works that are *not* among the site's own declared citations — a bibliography of the literature a guide discusses — is not what this role is for, and is not yet supported.

.. _guide-unresolvable-citations:

Unresolvable citations
======================

A card whose argument no entry answers to — and a card with no argument on a site that names no preferred citation — renders nothing and emits a build warning.
The warning restates the three ways an entry is selected and names a few of the site's entries as ``key (label)``, counting the rest rather than listing every one of them; an argument that is close to an entry's label, key, or DOI is answered with that entry instead.
The warning about a missing default asks for ``preferred = true``, since that is the field a site sets when the citation to use is published elsewhere; ``self = true`` answers it too, for a site that really is its DOI's landing page.

A ``doi`` role whose target no entry answers to warns the same way, and renders its target as unlinked text so the sentence around it still reads in the page that ships.

An argument *several* entries answer to — a shared :ref:`label <guide-project-citations-label>`, or a label that happens to equal another entry's key — warns too, naming the candidates by key and asking the page to select by key or by DOI.
The card renders nothing and the role renders plain text, as they do for a target that resolves to no entry at all.
No precedence is defined, so a label never quietly beats a key: either answer would be the wrong DOI on some page, with nothing on it to say so.

A role whose entry declares no DOI warns too, rather than linking that entry's :ref:`url <guide-project-citations-url>`.
The role's name is its contract: in the default spelling the link's *text* is the DOI, so linking a repository's landing page here would display that URL as though it were one.
Link such a work with ordinary hyperlink syntax, or show it with a :ref:`card <guide-citation-card>`, which displays whichever location the entry has.

Every one of those warnings carries the subtype ``documenteer.citation_card``, so a site that knowingly keeps an unresolved reference can stop it from failing a warnings-as-errors (``-W``) build:

.. code-block:: python

   # conf.py
   suppress_warnings = ["documenteer.citation_card"]

.. _guide-undated-citations:

Undated citations
=================

An entry that states no :ref:`date <guide-project-citations-date>` — and whose :ref:`cff <guide-project-citations-cff>` file supplies none either — is cited undated wherever the site shows it: the plain text loses its ``(YYYY)``, the BibTeX entry carries no ``year`` field, and the BibTeX key is built from the author and title alone.
Nothing on the rendered page says so, which is why the build does.

Each such entry emits one ``documenteer.citation_date`` warning, naming the entry — by its :ref:`label <guide-project-citations-label>`, or by its title when it has none — and where the date belongs.
That is the entry's own ``date`` field, and, for an entry reading a :file:`CITATION.cff` file, ``date-released`` (or ``year``) in the record it reads there: the file's ``preferred-citation``, or its top-level record when :ref:`cff_preferred = false <guide-project-citations-cff-preferred>` selects that one.
Naming the record matters, because a file whose top-level software record carries no date at all can sit above a dated ``preferred-citation``.

A :ref:`software <guide-project-citations-type>` entry located by a :ref:`url <guide-project-citations-url>` rather than by a DOI is the exception, and is not reported.
Software released continuously has no publication event to date — its :ref:`version <guide-project-citations-version>` is what identifies the code a reader ran, and the date that qualifies it is the date they accessed it — so reporting such an entry would make ``suppress_warnings`` the end state of every package site, silencing the dated works its author *does* want to hear about.
Software that carries a DOI is reported like any other work, because DataCite requires a publication year of every DOI, and so is an entry reading a :file:`CITATION.cff` file's ``preferred-citation``, which names a work other than the repository the file describes.

Rendering is unchanged either way, so a site with no date to give silences it by name:

.. code-block:: python

   # conf.py
   suppress_warnings = ["documenteer.citation_date"]

.. _guide-footer-citations:

Footer citations
================

The site footer shows the citations on every page, which is what makes each page of the guide a landing page for the site's DOI rather than only the page that carries a card.
They open the footer, above the horizontal rule that separates them from the Rubin Observatory links, copyright, and funding statement every guide shares: those are the same everywhere, and the citations are this site's own.

The footer shows the site's :ref:`preferred <guide-project-citations-preferred>` citation, its :ref:`self <guide-project-citations-self>` entry, and every entry that sets :ref:`in_footer = true <guide-project-citations-in-footer>`, in the order :file:`documenteer.toml` declares them.
The first two are one entry on a site that publishes its own DOI, so such a site shows one citation.
A site that separates them shows both, and writes :ref:`in_footer = false <guide-project-citations-in-footer>` on one to show only the other.
Each one shows the same three parts a card does — the :ref:`label <guide-project-citations-label>`, the citation with its DOI as a ``https://doi.org/`` hyperlink, and the :ref:`note <guide-project-citations-note>` — under a "How to cite" heading.
With the configuration above, the footer reads:

.. code-block:: text

   How to cite

   DATASET

   Vera C. Rubin Observatory (2025). Data Preview 2. Vera C. Rubin
   Observatory. https://doi.org/10.71929/rubin/2570308

   To be used when citing the DP2 dataset and this documentation.

Each entry also carries the same collapsed ``BibTeX`` disclosure and ``Copy BibTeX`` button a :ref:`card <guide-citation-card>` does, so a reader can take the entry from whichever surface they are looking at.

A guide that declares no citations, and one whose entries all set ``in_footer = false``, renders no citations block at all.
The script behind the copy buttons is referenced by the pages that have one — every page of a site whose footer shows a citation, and otherwise the pages that carry a :ref:`card <guide-citation-card>` — so a guide that displays no citation loads nothing.

.. _guide-citation-api-heavy:

Sites with a large API reference
================================

A package guide is mostly generated API pages, and a footer citation appears under every one of them.
That is the right default for a data release, whose pages a reader arrives at from a DOI; it is noise on a site where a hundred pages document one function each.

Such a site writes :ref:`in_footer = false <guide-project-citations-in-footer>` on its :ref:`preferred <guide-project-citations-preferred>` entry and shows the citation once, on the page a reader looking for it would visit:

.. code-block:: toml

   [[project.citations]]
   url = "https://github.com/lsst-sqre/safir"
   type = "software"
   label = "Safir"
   preferred = true
   in_footer = false
   title = "Safir"
   authors = [{ name = "Vera C. Rubin Observatory" }]

.. code-block:: rst

   .. citation-card::

Nothing is lost by silencing the footer.
``in_footer`` governs the visible surfaces alone: the preferred citation is still described in full in the :ref:`site-wide JSON-LD block <guide-citation-metadata>` that every page of the site carries, so a crawler finds it wherever it lands, and a reader who arrives at the home page meets the card.
The copy script follows the button, so only the page with the card loads it.

.. _guide-citation-pages:

Landing pages inside the site
=============================

A site is the landing page of one DOI — the entry marked :ref:`self = true <guide-project-citations-self>` — and every page of it carries that DOI's metadata.
A site that publishes *several* works can do better than that.
Data Preview 2, for example, mints a DOI per data product, and each of those DOIs resolves to the product's own page inside ``dp2.lsst.io`` rather than to the site root.
Those pages are the registered landing pages of those DOIs, so they, not the home page, should be the ones saying so.

An entry says which page is its landing page with :ref:`page <guide-project-citations-page>`, a Sphinx docname, and names the work within that page with a fragment.
Give each work an explicit target in the page's source, above the heading that documents it:

.. code-block:: rst

   .. _object-butler:

   Butler
   ------

   .. _object-tap:

   TAP
   ---

and claim those targets:

.. code-block:: toml

   # documenteer.toml

   [project.citation_defaults]
   type = "dataset"
   publisher = "Vera C. Rubin Observatory"
   date = 2025-06-30
   authors = [{ name = "Vera C. Rubin Observatory" }]

   [[project.citations]]
   doi = "10.71929/rubin/2570308"
   label = "Release"
   self = true
   title = "Data Preview 2"

   [[project.citations]]
   doi = "10.71929/rubin/3382539"
   label = "Butler"
   page = "products/catalogs/object#object-butler"
   title = "DP2 Object catalog"

   [[project.citations]]
   doi = "10.71929/rubin/3382540"
   label = "TAP"
   page = "products/catalogs/object#object-tap"
   title = "DP2 Object catalog"

A release's products are published by the same observatory, in the same year, and are all datasets, so those fields are stated once in :ref:`[project.citation_defaults] <guide-project-citation-defaults>` and each entry is the four fields that tell one product from the next.
An entry that states a field of its own — a product with a different release date, or a paper the site cites — overrides the default, and a :file:`CITATION.cff` file the entry names beats it too.

The labels are the words the page needs under its ``Butler`` and ``TAP`` headings, not names that tell the site's forty entries apart — every product has a TAP entry, so ``label = "TAP"`` repeats across the site.
That is what labels are for; the DOI is what selects.

With that configuration, :file:`products/catalogs/object.html` describes the two catalog DOIs — each located at its own fragment, ``#object-butler`` and ``#object-tap`` — instead of the release DOI.
Because the page is the landing page of two DOIs, it emits a JSON-LD ``@graph`` of both and no citation meta tags at all: every one of those tags is single-valued, and the page has no single title, DOI, or date to give.
A page a single entry claims does emit them, carrying that entry's DOI.

An explicit target, rather than the anchor a heading generates from its own text, is what a fragment registered against a DOI should be.
A generated anchor is derived from the heading: rewording "TAP" to "TAP service" turns ``#tap`` into ``#tap-service``, and the URL DataCite holds for that DOI stops resolving to anything on the page.
Nothing about that build fails, and the symptom surfaces at doi.org months later, to someone other than whoever reworded the heading.
An explicit target is the author's to name and to keep.

Every page no entry claims — the home page, the rest of the guide — is unchanged and keeps the release DOI's metadata.
The claim also relates the two works: each catalog's node names the release as the work it is ``isPartOf``, and the release's own node names both catalogs under ``hasPart``, so a consumer arriving at either end can reach the other (see :ref:`guide-citation-metadata`).

Those ``hasPart`` references are the one thing a claimed page adds to *every* page of the site, since the site-wide block is emitted on all of them.
Each is a reference alone — a schema.org type, a DOI, and a title — which runs to roughly 150 bytes of JSON-LD, so a release with forty product DOIs adds a few kilobytes to every page.
That is the cost of the relation, and it is why an entry names a page by reference there and carries its full record only on the page it claims.

Claiming a page changes only the machine-readable metadata; the visible surfaces are unaffected.
The footer still shows the same citations everywhere, and ``.. citation-card::`` with no argument still renders the site's preferred citation.
A landing page that wants to show the citation a reader arriving from doi.org came for names it by DOI, since its label is shared with every other product's TAP entry:

.. code-block:: rst

   .. citation-card:: 10.71929/rubin/3382540

A ``page`` value the build cannot resolve emits a ``documenteer.citation_page`` warning and leaves the entry working everywhere else.
That covers both halves of the claim: a docname the project does not contain — a renamed page, or a value written as a file path rather than a docname — and a fragment that names no anchor on the page it claims, whose warning also names the explicit targets that page does record, so a claim broken by a renamed target says what to claim instead.

.. _guide-citation-metadata:

Related metadata
================

Declaring ``[[project.citations]]`` also makes the site's citation machine-readable: every page's ``<head>`` carries the ``self`` citation as Highwire and Dublin Core meta tags, along with a schema.org JSON-LD description of the site.
Each citation's :ref:`type <guide-project-citations-type>` decides the schema.org type it is described under there, so ``type = "dataset"`` is what makes a data release indexable by Google Dataset Search.
A citation's :ref:`version <guide-project-citations-version>` reaches the two types that define a property for one — ``softwareVersion`` on a `SoftwareSourceCode <https://schema.org/SoftwareSourceCode>`__ and ``version`` on a `Dataset <https://schema.org/Dataset>`__ — and no other node states it.

Highwire meta tags are what `Google Scholar's inclusion guidelines <https://scholar.google.com/intl/en/scholar/inclusion.html>`__ specify and what Zotero's embedded-metadata translator reads, so a reader on a page that carries them gets a one-click "Save to Zotero" with the right title, creators, date, and DOI.
These are the tags emitted, in this order:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Tag
     - Value
   * - ``citation_title``
     - :ref:`title <guide-project-citations-title>`
   * - ``citation_author``
     - one per :ref:`author <guide-project-citations-authors>`, family name first; an organization's name whole
   * - ``citation_author_institution``
     - that author's ``affiliation``, when set
   * - ``citation_author_orcid``
     - that author's ``orcid`` as a resolvable ``https://orcid.org/`` URL, when set
   * - ``citation_publication_date``
     - :ref:`date <guide-project-citations-date>` as ``YYYY/MM/DD``, or as ``YYYY`` when the entry dates the work to the year or the month
   * - ``citation_doi``
     - :ref:`doi <guide-project-citations-doi>`, bare
   * - ``citation_publisher``
     - :ref:`publisher <guide-project-citations-publisher>`
   * - ``citation_fulltext_html_url``
     - the page's own URL, which needs :ref:`base_url <guide-project-base-url>`
   * - ``DC.identifier``
     - the DOI as a resolvable ``https://doi.org/`` URL, the Dublin Core complement DataCite's landing-page guidance asks for

A field the entry does not state emits no tag, so an entry :ref:`located by url <guide-project-citations-url>` rather than by a DOI carries no ``citation_doi`` and no ``DC.identifier``.
Every value is HTML-escaped, so a title containing quotes or angle brackets reaches the tag intact.

.. note::

   Documenteer writes the date tag as ``citation_publication_date``, the spelling Google Scholar documents.
   A Rubin technote built with technote 0.11.0 or later writes the same tag; earlier releases spelled it ``citation_date``, and a consumer reads either.

   Google Scholar's inclusion guidelines describe only two forms for the value — a full date, or a year alone — so an entry dated to the month states its year in this tag rather than a ``2025/06`` no guideline covers, which Scholar may not parse at all.
   The month is not lost: the schema.org ``datePublished`` in the page's JSON-LD block carries the entry's date at the precision it states, ``2025-06`` included.

That JSON-LD block is *about* the ``self`` entry, and states every other entry as a relation of it rather than repeating the whole record:

- An entry that names a :ref:`page <guide-project-citations-page>` is a **part** of the site's own work — a data product of a release, say, not something the site cites.
  The site-wide block names it under ``hasPart`` by reference alone: its schema.org type, its DOI, and its title, and nothing more.
  The full record lives on the page the entry claims, whose own block points back at the site with an ``isPartOf`` reference of the same shape.
- An entry with **no** page is a work the site **cites**, and reaches the site-wide block in full.
  The :ref:`preferred <guide-project-citations-preferred>` entry always does: it is the citation the site asks readers to use, which is exactly what schema.org ``citation`` states, whether or not the footer repeats it.
  Any *other* entry reaches the block only when the site displays it, which is to say when :ref:`in_footer <guide-project-citations-in-footer>` is true.
- An entry that is neither a part, nor preferred, nor shown in the footer appears in no site-wide block at all, because no page of the site presents it.
  It still renders wherever a :ref:`citation-card <guide-citation-card>` names it.

So :ref:`in_footer <guide-project-citations-in-footer>` decides a visual surface, and — for the additional entries alone — whether the metadata carries them.
A site that writes ``in_footer = false`` on its preferred citation keeps the whole of this block; see :ref:`guide-citation-api-heavy`.

A site that marks no entry ``self`` is no DOI's landing page, so it emits **none** of the meta tags above on any page — not the title and authors either, since stating them would tell a harvester that this site is the full text of a work published somewhere else.
Marking an entry :ref:`preferred <guide-project-citations-preferred>` does not change that: ``preferred`` says which citation the site asks readers to use, which is a question for the visible surfaces, and only ``self`` claims that this site is where a DOI resolves.
Its JSON-LD block still has a subject — the site itself, a schema.org ``WebSite`` carrying the site's title and URL and no identifier — and the same entries reach it under the same two relations, in the same shapes.
Such a site can still be the landing page of someone else's DOI on a page of its own, and that page's block names this ``WebSite`` node under ``isPartOf``, so both ends of the relation are stated there too; the reference carries the site's title and URL in place of a DOI, since that is what identifies a site with no DOI to give.
Only the subject differs, so a consumer reads the block the same way whether or not the site publishes a DOI.

Keeping the parts to references is what lets a site publish a DOI per data product without paying for it on every page: a release with forty product DOIs states forty short references, not forty full records, and each product's own landing page carries the record that describes it.

See :ref:`[[project.citations]] <guide-project-citations>` for the full field reference.
