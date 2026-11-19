.. _guide-citation-pages:

#############################
Landing pages inside the site
#############################

A user guide can be the landing page for several DOIs, not just one for user guide as a whole (see :doc:`doi-landing-page`).
For example, Data Preview 2 provides a DOI per data product, and each of those DOIs resolves to the product's own page inside ``dp2.lsst.io`` rather than to the site root.
Those pages are the registered landing pages of those DOIs, so they, rather than the home page, should carry each DOI's metadata.

Example
=======

To associate a citation item in ``[[project.citations]]`` with a specific page, add a :ref:`page <guide-project-citations-page>` field to the citation entry:

.. grid:: 2

   .. grid-item::
      :columns: 12 12 8 8

      .. code-block:: toml
         :caption: documenteer.toml

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

   .. grid-item::
      :columns: 12 12 4 4

      .. tip::

         Since all the citation entries in this example share the same ``type``, ``publisher``, ``date``, and ``authors``, they can be written once in :ref:`[project.citation_defaults] <guide-project-citation-defaults>`.

These ``page`` values match with the docname, and optionally an anchor, in the content:

.. grid:: 2

   .. grid-item::
      :columns: 12 12 8 8

      .. code-block:: rst
         :caption: products/catalogs/object.rst

         .. _object-butler:

         Butler
         ------

         .. citation-card:: 10.71929/rubin/3382539

         [...]

         .. _object-tap:

         TAP
         ---

         .. citation-card:: 10.71929/rubin/3382540

         [...]

   .. grid-item::
      :columns: 12 12 4 4

      .. tip::

         Use an explicit target, rather than the anchor Sphinx generates from a heading's text, for a fragment registered against a DOI.
         A generated anchor is derived from the heading: rewording "TAP" to "TAP service" turns ``#tap`` into ``#tap-service``, and the URL DataCite holds for that DOI stops resolving to anything on the page.
         The build doesn't fail, and the broken link surfaces at doi.org months later, to someone other than the person who reworded the heading.
         An explicit target changes only when an author changes it deliberately.

Citation metadata with DOI landing pages
========================================

Configuring a page as the landing page for one or more DOIs impacts how :doc:`machine-readable metadata <metadata>` is included:

- A page that is the landing page for a single DOI emits the meta tags for that DOI.

- If a page is the landing page for multiple DOIs, as in the Butler and TAP example above, the page includes a a JSON-LD ``@graph`` of all citation entries for that page, but doesn't include the traditional HTML meta tags (such as Highwire and Dublin Core) that are single-valued.

- Every page that no corresponding citation entry keeps the citation metadata of the ``self`` citation entry (if one is set).

Adding page-level DOIs to a site with a self
Documenteer automatically relates the citations of page-level entries with a site's ``self`` citation entry with ``isPartOf`` and ``hasPart``.
In the above exaple, each catalog's node names the release as the work it is ``isPartOf``, and the release's own node names both catalogs under ``hasPart``, so a consumer arriving at either end can reach the other (see :ref:`guide-citation-metadata`).
Those ``hasPart`` references are the one thing a claimed page adds to *every* page of the site, since the site-wide block is emitted on all of them.
Each is a reference alone — a schema.org type, a DOI, and a title — which runs to roughly 150 bytes of JSON-LD, so a release with forty product DOIs adds a few kilobytes to every page.
That's the cost of stating the relation, and it's why the site-wide block names each claimed entry by reference, while the full record appears only on the page the entry claims.

Include a citation card on the DOI landing page or section
==========================================================

Claiming a page changes only the machine-readable metadata.
The visible surfaces are unaffected.
The footer still shows the same citations everywhere, and ``.. citation-card::`` with no argument still renders the site's :ref:`preferred <guide-project-citations-preferred>` citation.
To show the citation that a reader arriving from doi.org came for, a landing page selects it by DOI, since its label is shared with every other product's TAP entry:

.. code-block:: rst

   .. citation-card:: 10.71929/rubin/3382540

Integrity checks in the build
=============================

A ``page`` value that the build can't resolve emits a ``documenteer.citation_page`` warning and leaves the entry working everywhere else.
The warning covers both halves of the claim: a docname the project doesn't contain (a renamed page, or a value written as a file path rather than a docname) and a fragment that names no anchor on the page it claims.
For a missing fragment, the warning also lists the explicit targets that the page does define, so you can see what to claim instead.
See :ref:`guide-citation-page-warnings`.
