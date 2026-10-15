.. _guide-citation-troubleshooting:

#################################
Troubleshooting citation warnings
#################################

A citation that is declared but cannot be shown as the site asks is reported at build time rather than rendered wrong.
Each kind of report carries its own warning subtype, so a site that accepts one of them can suppress exactly that one with Sphinx's ``suppress_warnings`` and keep building with warnings as errors (``-W``).

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
A site that writes a :ref:`[project.citation_defaults] <guide-project-citation-defaults>` table is offered that too, named last because that is where the date resolves from last.
On a site that dates forty data products from one table, an undated entry is usually forty undated entries and a missing default, and the entry is the one place its author should not write the date.

A :ref:`software <guide-project-citations-type>` entry located by a :ref:`url <guide-project-citations-url>` rather than by a DOI is the exception, and is not reported.
Software released continuously has no publication event to date — its :ref:`version <guide-project-citations-version>` is what identifies the code a reader ran, and the date that qualifies it is the date they accessed it — so reporting such an entry would make ``suppress_warnings`` the end state of every package site, silencing the dated works its author *does* want to hear about.
Software that carries a DOI is reported like any other work, because DataCite requires a publication year of every DOI, and so is an entry reading a :file:`CITATION.cff` file's ``preferred-citation``, which names a work other than the repository the file describes.
What decides is the record the file supplied, not the entry's ``cff_preferred`` flag: an entry left at the default against a file that declares no ``preferred-citation`` read the file's top-level record, so it describes the repository and is exempt.
This site's own Software entry is one (see :doc:`cff`).

Rendering is unchanged either way, so a site with no date to give silences it by name:

.. code-block:: python

   # conf.py
   suppress_warnings = ["documenteer.citation_date"]

.. _guide-citation-page-warnings:

Unresolvable landing pages
==========================

An entry's :ref:`page <guide-project-citations-page>` claims a page of the site as the landing page of that entry's DOI (see :doc:`site-pages`).
A ``page`` value the build cannot resolve emits a ``documenteer.citation_page`` warning and leaves the entry working everywhere else: the entry still renders on cards and in the footer, and the pages no entry claims are unchanged.

The warning covers both halves of the claim.
A docname the project does not contain — a renamed page, or a value written as a file path rather than a docname — is reported as such.
A fragment that names no anchor on the page it claims is reported with the explicit targets that page does record, so a claim broken by a renamed target says what to claim instead.

A site that knowingly keeps such a claim, for a page that is built elsewhere, say, silences the warning by name:

.. code-block:: python

   # conf.py
   suppress_warnings = ["documenteer.citation_page"]

.. _guide-citation-rebuild:

An edit to the citations did not appear
=======================================

A :ref:`card <guide-citation-card>` and a :ref:`doi role <guide-citation-doi-role>` resolve their entry while the page is *read*, and the rendered result is cached with the page's doctree.
So that an edit to ``[[project.citations]]`` reaches them, the guide preset publishes a digest of the resolved citations as a configuration value whose change invalidates the environment: the build after a citation edit re-reads every document, and Sphinx says why in its log (``updating environment: [config changed ('documenteer_citations_digest')]``).
That build takes as long as a fresh one.
A build whose citations are unchanged — including one where :file:`documenteer.toml` was rewritten cosmetically, or edited somewhere other than its citations — is still incremental and re-reads nothing.

A full re-read over a warm build directory can surface warnings a fresh build does not, such as autodoc's ``duplicate object description`` on a project whose API reference is documented from two places.
Those warnings are not caused by the citations, and a project that builds with ``-W`` over a persistent doctree directory should expect the first build after a citation edit to report them; a fresh build (``-E``, or a cleared build directory) is the reference.
