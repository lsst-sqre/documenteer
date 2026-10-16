.. _guide-citation-metadata:

#########################
Machine-readable metadata
#########################

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
     - the site's root URL for the :ref:`self <guide-project-citations-self>` entry, which is the URL that DOI is registered against; the claimed page's own URL — with the claim's fragment, when it names one — for an entry that sets :ref:`page <guide-project-citations-page>`.
       Either needs :ref:`base_url <guide-project-base-url>`, and neither is emitted without one
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

This site is one of those.
It :ref:`declares two citations <guide-citations>` and marks neither ``self``, so viewing the source of this page finds no ``citation_title`` or ``DC.identifier`` tag in its ``<head>``.
It does find one ``application/ld+json`` block, whose subject is a ``WebSite`` named Documenteer, with the Software entry, the preferred citation, described in full under ``citation`` as a ``SoftwareSourceCode``.
The Paper entry is in neither: it is not preferred and not shown in the footer, so no page of the site presents it except the ones that render it on a card.

Keeping the parts to references is what lets a site publish a DOI per data product without paying for it on every page: a release with forty product DOIs states forty short references, not forty full records, and each product's own landing page carries the record that describes it.

See :ref:`[[project.citations]] <guide-project-citations>` for the full field reference.
