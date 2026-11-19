.. _guide-citation-troubleshooting:

#################################
Troubleshooting citation warnings
#################################

A citation that's declared but can't be shown as the site asks is reported at build time rather than rendered incorrectly.
Each kind of report carries its own warning subtype, so a site that accepts one of them can suppress exactly that one with Sphinx's ``suppress_warnings`` and keep building with warnings as errors (``-W``).

.. _guide-unresolvable-citations:

Unresolvable citations
======================

A card whose argument matches no entry, or a card with no argument on a site that names no preferred citation, renders nothing and emits a build warning.
The warning restates the three ways to select an entry and names a few of the site's entries as ``key (label)``, with a count of the rest.
When the argument is close to an entry's label, key, or DOI, the warning suggests that entry instead.
The warning about a missing default asks for :ref:`preferred = true <guide-project-citations-preferred>`, since that's the field to set when the work to cite is published elsewhere.
:ref:`self = true <guide-project-citations-self>` also resolves it, for a site that really is its DOI's landing page.

A ``doi`` role whose target matches no entry warns the same way, and renders its target as unlinked text so the surrounding sentence still reads correctly on the published page.

An argument that *several* entries match (a shared :ref:`label <guide-project-citations-label>`, or a label that happens to equal another entry's key) warns too, naming the candidates by key and asking the page to select by key or by DOI.
The card renders nothing and the role renders plain text, as they do for a target that resolves to no entry at all.
No precedence is defined, so a label never silently wins over a key: either choice would put the wrong DOI on some page, with nothing to indicate the mistake.

A role whose entry declares no DOI warns too, rather than linking that entry's :ref:`url <guide-project-citations-url>`.
The role promises a DOI: by default the link's *text* is the DOI, so linking a repository's landing page here would display that URL as though it were a DOI.
Link such a work with ordinary hyperlink syntax, or show it with a :ref:`card <guide-citation-card>`, which displays whichever location the entry has.

Every one of those warnings carries the subtype ``documenteer.citation_card``, so a site that knowingly keeps an unresolved reference can stop it from failing a warnings-as-errors (``-W``) build:

.. code-block:: python
   :caption: conf.py

   suppress_warnings = ["documenteer.citation_card"]

.. _guide-undated-citations:

Undated citations
=================

An entry that states no :ref:`date <guide-project-citations-date>`, and whose :ref:`cff <guide-project-citations-cff>` file supplies none either, is cited without a date wherever the site shows it: the plain text loses its ``(YYYY)``, the BibTeX entry carries no ``year`` field, and the BibTeX key is built from the author and title alone.
Nothing on the rendered page points this out, so the build does.

Each such entry emits one ``documenteer.citation_date`` warning that names the entry (by its :ref:`label <guide-project-citations-label>`, or by its title when it has none) and says where the date belongs.
The date belongs in the entry's own ``date`` field or, for an entry reading a :file:`CITATION.cff` file, in ``date-released`` (or ``year``) in the record it reads: the file's ``preferred-citation``, or its top-level record when :ref:`cff_preferred = false <guide-project-citations-cff-preferred>` selects that one.
Naming the record matters, because a file can have an undated top-level software record alongside a dated ``preferred-citation``.
On a site that has a :ref:`[project.citation_defaults] <guide-project-citation-defaults>` table, the warning lists that table too, last, because it's the last place the date resolves from.
On a site that dates forty data products from one table, an undated entry usually means forty undated entries and a missing default, and the fix belongs in the defaults table rather than on each entry.

A :ref:`software <guide-project-citations-type>` entry located by a :ref:`url <guide-project-citations-url>` rather than by a DOI is the exception, and isn't reported.
Continuously released software has no publication event to date: its :ref:`version <guide-project-citations-version>` identifies the code a reader ran, and the relevant date is the date they accessed it.
Reporting such entries would push every package site to set ``suppress_warnings``, which would also silence warnings about works that *should* be dated.
Software that carries a DOI is reported like any other work, because DataCite requires a publication year of every DOI, and so is an entry reading a :file:`CITATION.cff` file's ``preferred-citation``, which names a work other than the repository the file describes.
The record that the file supplied decides this, not the entry's ``cff_preferred`` flag: an entry left at the default, reading a file that declares no ``preferred-citation``, gets the file's top-level record, so it describes the repository and is exempt.
This site's own Software entry is an example (see :doc:`cff`).

The warning doesn't change what's rendered, so a site with no date to give can suppress it by name:

.. code-block:: python
   :caption: conf.py

   suppress_warnings = ["documenteer.citation_date"]

.. _guide-citation-page-warnings:

Unresolvable landing pages
==========================

An entry's :ref:`page <guide-project-citations-page>` claims a page of the site as the landing page of that entry's DOI (see :doc:`site-pages`).
A ``page`` value that the build can't resolve emits a ``documenteer.citation_page`` warning and leaves the entry working everywhere else: the entry still renders on cards and in the footer, and the pages no entry claims are unchanged.

The warning covers both halves of the claim.
A docname the project doesn't contain — a renamed page, or a value written as a file path rather than a docname — is reported as such.
A fragment that names no anchor on the page it claims is reported along with the explicit targets that the page does define, so you can see what to claim instead.

A site that knowingly keeps such a claim (for a page that's built elsewhere, for example) can suppress the warning by name:

.. code-block:: python
   :caption: conf.py

   suppress_warnings = ["documenteer.citation_page"]

.. _guide-citation-rebuild:

An edit to the citations did not appear
=======================================

A :ref:`card <guide-citation-card>` and a :ref:`doi role <guide-citation-doi-role>` resolve their entry while the page is *read*, and the rendered result is cached with the page's doctree.
So that an edit to :ref:`[[project.citations]] <guide-project-citations>` reaches them, the guide preset publishes a digest of the resolved citations as a configuration value whose change invalidates the environment: the build after a citation edit re-reads every document, and Sphinx says why in its log (``updating environment: [config changed ('documenteer_citations_digest')]``).
That build takes as long as a fresh one.
A build whose citations are unchanged — including one where :file:`documenteer.toml` was rewritten cosmetically, or edited somewhere other than its citations — is still incremental and re-reads nothing.

A full re-read over a warm build directory can surface warnings a fresh build does not, such as autodoc's ``duplicate object description`` on a project whose API reference is documented from two places.
Those warnings aren't caused by the citations.
A project that builds with ``-W`` over a persistent doctree directory should expect the first build after a citation edit to report them, and should compare against a fresh build (``-E``, or a cleared build directory).
