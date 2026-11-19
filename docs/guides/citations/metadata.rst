.. _guide-citation-metadata:

#########################
Machine-readable metadata
#########################

Declaring :ref:`[[project.citations]] <guide-project-citations>` also makes the site's citation machine-readable: every page's ``<head>`` carries the :ref:`self <guide-project-citations-self>` citation as Highwire and Dublin Core meta tags, along with a schema.org JSON-LD description of the site.
Each citation's :ref:`type <guide-project-citations-type>` sets the schema.org type it's described as, so ``type = "dataset"`` is what makes a data release indexable by Google Dataset Search.
A citation's :ref:`version <guide-project-citations-version>` appears on the two types that define a property for it, ``softwareVersion`` on a `SoftwareSourceCode <https://schema.org/SoftwareSourceCode>`__ and ``version`` on a `Dataset <https://schema.org/Dataset>`__, and on no other node.

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
     - one per :ref:`author <guide-project-citations-authors>`, family name first (an organization's name is written whole)
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
     - For the :ref:`self <guide-project-citations-self>` entry, the site's root URL, which is the URL that DOI is registered against.
       For an entry that sets :ref:`page <guide-project-citations-page>`, the claimed page's own URL, with the claim's fragment when it names one.
       Both need :ref:`base_url <guide-project-base-url>`, and the tag isn't emitted without it.
   * - ``DC.identifier``
     - the DOI as a resolvable ``https://doi.org/`` URL, the Dublin Core complement DataCite's landing-page guidance asks for

A field that the entry doesn't state emits no tag, so an entry :ref:`located by url <guide-project-citations-url>` rather than by a DOI carries no ``citation_doi`` and no ``DC.identifier``.
Every value is HTML-escaped, so a title containing quotes or angle brackets reaches the tag intact.

.. note::

   Documenteer writes the date tag as ``citation_publication_date``, the spelling Google Scholar documents.
   A Rubin technote built with technote 0.11.0 or later writes the same tag.
   Earlier releases spelled it ``citation_date``, and consumers read either.

   Google Scholar's inclusion guidelines describe only two forms for the value — a full date, or a year alone — so an entry dated to the month states only its year in this tag, rather than a ``2025/06`` form that no guideline covers and that Scholar may not parse.
   The month isn't lost: the schema.org ``datePublished`` in the page's JSON-LD block carries the entry's date at the precision it states, ``2025-06`` included.

The JSON-LD block is *about* the ``self`` entry, and describes every other entry by its relation to it:

- An entry that names a :ref:`page <guide-project-citations-page>` is a **part** of the site's own work (a data product of a release, for example), not something the site cites.
  The site-wide block names it under ``hasPart`` by reference alone: its schema.org type, its DOI, and its title, and nothing more.
  The full record lives on the page the entry claims, whose own block points back at the site with an ``isPartOf`` reference of the same shape.
- An entry with **no** page is a work the site **cites**, and the site-wide block describes it in full.
  The :ref:`preferred <guide-project-citations-preferred>` entry is always included, whether or not the footer shows it, because it's the citation the site asks readers to use, which is what schema.org ``citation`` states.
  Any *other* entry is included only when the site displays it in the footer, that is, when :ref:`in_footer <guide-project-citations-in-footer>` is true.
- An entry that's not a part, not preferred, and not shown in the footer doesn't appear in the site-wide block at all, because the site doesn't display it by default.
  It still renders wherever a :ref:`citation-card <guide-citation-card>` names it.

So :ref:`in_footer <guide-project-citations-in-footer>` controls a visible surface and, for the additional entries only, whether the metadata includes them.
A site that sets ``in_footer = false`` on its preferred citation keeps the whole block.

A site that marks no entry ``self`` isn't any DOI's landing page, so it emits **none** of the meta tags above on any page.
That includes the title and authors, since stating them would tell a harvester that this site is the full text of a work published somewhere else.
Marking an entry :ref:`preferred <guide-project-citations-preferred>` doesn't change that: ``preferred`` says which citation the site asks readers to use, which affects the visible surfaces, and only ``self`` claims that this site is where a DOI resolves.
The site's JSON-LD block still has a subject: the site itself, a schema.org ``WebSite`` carrying the site's title and URL and no identifier.
The same entries appear in it under the same two relations, in the same form.
Such a site can still be the landing page of a DOI on one of its own pages, and that page's block names this ``WebSite`` node under ``isPartOf``, so both ends of the relation are stated there too.
The reference carries the site's title and URL in place of a DOI, since those are what identify a site that has no DOI.
Only the subject differs, so a consumer reads the block the same way whether or not the site publishes a DOI.

This site is an example.
It :ref:`declares two citations <guide-citations>` and marks neither ``self``, so the source of this page has no ``citation_title`` or ``DC.identifier`` tag in its ``<head>``.
It does have one ``application/ld+json`` block, whose subject is a ``WebSite`` named Documenteer, with the Software entry (the preferred citation) described in full under ``citation`` as a ``SoftwareSourceCode``.
The Paper entry isn't in the block: it's not preferred and not shown in the footer, so it appears only on pages that render it in a card.

Describing parts by reference lets a site publish a DOI per data product without adding a full record to every page: a release with forty product DOIs states forty short references, not forty full records, and each product's own landing page carries the record that describes it.

See :ref:`[[project.citations]] <guide-project-citations>` for the full field reference.
