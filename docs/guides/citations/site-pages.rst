.. _guide-citation-pages:

#############################
Landing pages inside the site
#############################

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
   publisher = "NSF-DOE Vera C. Rubin Observatory"
   date = 2025-06-30
   authors = [{ name = "NSF-DOE Vera C. Rubin Observatory" }]

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
See :ref:`guide-citation-page-warnings`.
