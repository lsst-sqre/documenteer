.. default-domain:: rst

.. _guide-citations:

#########
Citations
#########

A site that is published with a DOI is that DOI's *landing page*, and a landing page is expected to show the reader a complete bibliographic citation with the DOI written as a resolvable ``https://doi.org/`` link.
A guide displays its citations in two places:

- The :ref:`site footer <guide-footer-citations>`, on every page.
- A :ref:`citation card <guide-citation-card>`, wherever a page asks for one.

Both read the same citations, so the two can never disagree about what the site asks to be cited as.

Declaring the citations
=======================

Both surfaces render the citations the site declares in the :ref:`[[project.citations]] <guide-project-citations>` array of :file:`documenteer.toml`; neither carries bibliographic fields of its own.
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
    It is what a card with no argument renders, and what the footer shows by default.

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

Such a repository is often worth citing twice — the paper for the work, and the package for the code that was run.
A second entry against the same file, with :ref:`cff_preferred = false <guide-project-citations-cff-preferred>`, reads the file's top-level record rather than its preferred citation:

.. code-block:: toml

   # documenteer.toml

   [[project.citations]]
   cff = "../CITATION.cff"
   cff_preferred = false
   label = "Software"
   in_footer = true
   note = "Cite the package itself when reporting the version you ran."

A package that has never been deposited for a DOI is cited by where it lives: the file's ``url``, or its ``repository-code`` when it names no landing page.
Only the :ref:`self <guide-project-citations-self>` entry needs a DOI, because that entry is the claim that this site is a DOI's landing page.

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

   **Selecting a citation by label**

   The optional argument is the :ref:`label <guide-project-citations-label>` of the entry to render, so a page can also show a citation that isn't the site's own:

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

   **Options**

   ``class``
       Additional CSS classes to set on the card.

   ``name``
       A cross-reference target for the card.

Unresolvable cards
==================

A card that names a label no entry carries — and a card with no argument on a site that names no preferred citation — renders nothing and emits a build warning naming the labels the site does declare.
The warning about a missing default asks for ``preferred = true``, since that is the field a site sets when the citation to use is published elsewhere; ``self = true`` answers it too, for a site that really is its DOI's landing page.

That warning carries the subtype ``documenteer.citation_card``, so a site that knowingly keeps such a card can stop it from failing a warnings-as-errors (``-W``) build:

.. code-block:: python

   # conf.py
   suppress_warnings = ["documenteer.citation_card"]

.. _guide-footer-citations:

Footer citations
================

The site footer shows the citations on every page, which is what makes each page of the guide a landing page for the site's DOI rather than only the page that carries a card.

The footer shows the site's :ref:`preferred <guide-project-citations-preferred>` citation and every entry that sets :ref:`in_footer = true <guide-project-citations-in-footer>`, in the order :file:`documenteer.toml` declares them.
Each one shows the same three parts a card does — the :ref:`label <guide-project-citations-label>`, the citation with its DOI as a ``https://doi.org/`` hyperlink, and the :ref:`note <guide-project-citations-note>` — under a "How to cite" heading.
With the configuration above, the footer reads:

.. code-block:: text

   How to cite

   DATASET

   Vera C. Rubin Observatory (2025). Data Preview 2. Vera C. Rubin
   Observatory. https://doi.org/10.71929/rubin/2570308

   To be used when citing the DP2 dataset and this documentation.

A guide that declares no citations, and one whose entries all set ``in_footer = false``, renders no citations block at all.

.. _guide-citation-pages:

Landing pages inside the site
=============================

A site is the landing page of one DOI — the entry marked :ref:`self = true <guide-project-citations-self>` — and every page of it carries that DOI's metadata.
A site that publishes *several* works can do better than that.
Data Preview 2, for example, mints a DOI per data product, and each of those DOIs resolves to the product's own page inside ``dp2.lsst.io`` rather than to the site root.
Those pages are the registered landing pages of those DOIs, so they, not the home page, should be the ones saying so.

An entry says which page is its landing page with :ref:`page <guide-project-citations-page>`, a Sphinx docname:

.. code-block:: toml

   # documenteer.toml

   [[project.citations]]
   doi = "10.71929/rubin/2570308"
   label = "Release"
   type = "dataset"
   self = true
   title = "Data Preview 2"
   publisher = "Vera C. Rubin Observatory"
   date = 2025-06-30
   authors = [{ name = "Vera C. Rubin Observatory" }]

   [[project.citations]]
   doi = "10.71929/rubin/3382539"
   label = "Object catalog (Butler)"
   type = "dataset"
   page = "products/catalogs/object#butler"
   title = "DP2 Object catalog"
   publisher = "Vera C. Rubin Observatory"
   date = 2025-06-30
   authors = [{ name = "Vera C. Rubin Observatory" }]

   [[project.citations]]
   doi = "10.71929/rubin/3382540"
   label = "Object catalog (TAP)"
   type = "dataset"
   page = "products/catalogs/object#tap"
   title = "DP2 Object catalog"
   publisher = "Vera C. Rubin Observatory"
   date = 2025-06-30
   authors = [{ name = "Vera C. Rubin Observatory" }]

With that configuration, :file:`products/catalogs/object.html` describes the two catalog DOIs — each located at its own fragment, ``#butler`` and ``#tap`` — instead of the release DOI.
Because the page is the landing page of two DOIs, it emits a JSON-LD ``@graph`` of both and no ``citation_doi`` or ``DC.identifier`` meta tag: those tags carry a single identifier, and the page has no single one to give.
A page a single entry claims does emit them, carrying that entry's DOI.

Every page no entry claims — the home page, the rest of the guide — is unchanged and keeps the release DOI's metadata.
The claim also relates the two works: each catalog's node names the release as the work it is ``isPartOf``, and the release's own node names both catalogs under ``hasPart``, so a consumer arriving at either end can reach the other (see :ref:`guide-citation-metadata`).

Claiming a page changes only the machine-readable metadata; the visible surfaces are unaffected.
The footer still shows the same citations everywhere, and ``.. citation-card::`` with no argument still renders the site's preferred citation.
A landing page that wants to show the citation a reader arriving from doi.org came for names it by label:

.. code-block:: rst

   .. citation-card:: Object catalog (TAP)

A ``page`` value naming a docname the project does not contain — a renamed page, or a value written as a file path rather than a docname — emits a ``documenteer.citation_page`` warning and leaves the entry working everywhere else.

.. _guide-citation-metadata:

Related metadata
================

Declaring ``[[project.citations]]`` also makes the site's DOI machine-readable: every page's ``<head>`` carries the ``self`` citation's DOI as Highwire and Dublin Core meta tags, along with a schema.org JSON-LD description of the site.
Each citation's :ref:`type <guide-project-citations-type>` decides the schema.org type it is described under there, so ``type = "dataset"`` is what makes a data release indexable by Google Dataset Search.

That JSON-LD block is *about* the ``self`` entry, and states every other entry as a relation of it rather than repeating the whole record:

- An entry that names a :ref:`page <guide-project-citations-page>` is a **part** of the site's own work — a data product of a release, say, not something the site cites.
  The site-wide block names it under ``hasPart`` by reference alone: its schema.org type, its DOI, and its title, and nothing more.
  The full record lives on the page the entry claims, whose own block points back at the site with an ``isPartOf`` reference of the same shape.
- An entry with **no** page is a work the site **cites**, and reaches the site-wide block in full — but only when the site displays it, which is to say when :ref:`in_footer <guide-project-citations-in-footer>` is true.
- An entry that is neither a part nor shown in the footer appears in no site-wide block at all, because no page of the site mentions it.
  It still renders wherever a :ref:`citation-card <guide-citation-card>` names it by label.

A site that marks no entry ``self`` publishes no DOI of its own, so it emits no ``citation_doi`` or ``DC.identifier`` meta tag on any page.
Its JSON-LD block still has a subject — the site itself, a schema.org ``WebSite`` carrying the site's title and URL and no identifier — and the same entries reach it under the same two relations, in the same shapes.
Only the subject differs, so a consumer reads the block the same way whether or not the site publishes a DOI.

Keeping the parts to references is what lets a site publish a DOI per data product without paying for it on every page: a release with forty product DOIs states forty short references, not forty full records, and each product's own landing page carries the record that describes it.

See :ref:`[[project.citations]] <guide-project-citations>` for the full field reference.
