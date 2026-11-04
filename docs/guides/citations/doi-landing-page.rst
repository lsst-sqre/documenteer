.. _guide-citation-landing-page:

########################################
Publishing a guide as a DOI landing page
########################################

A site that is published with a DOI is that DOI's *landing page*: the URL that doi.org resolves the DOI to.
DataCite expects a landing page to show the reader a complete bibliographic citation, to write the DOI as a resolvable ``https://doi.org/`` link, and to state the same metadata in a machine-readable form.
Declaring the DOI's citation with :ref:`self = true <guide-project-citations-self>` is how a guide meets all three.

Declaring the site's own DOI
============================

A site that documents a data release typically declares two citations: the release itself, which this site is the landing page for, and the paper that describes it:

.. code-block:: toml

   # documenteer.toml

   [[project.citations]]
   doi = "10.71929/rubin/2570308"
   label = "Dataset"
   type = "dataset"
   self = true
   note = "To be used when citing the DP2 dataset and this documentation."
   title = "Data Preview 2"
   publisher = "NSF-DOE Vera C. Rubin Observatory"
   date = 2025-06-30
   authors = [{ name = "NSF-DOE Vera C. Rubin Observatory" }]

   [[project.citations]]
   doi = "10.5281/zenodo.1234567"
   label = "Paper"
   type = "article"
   title = "The Data Preview 2 release"
   publisher = "Zenodo"
   date = 2025-06-30
   authors = [{ name = "NSF-DOE Vera C. Rubin Observatory" }]

The ``self`` entry is the claim that this site is where that DOI resolves, so the entry must have a :ref:`doi <guide-project-citations-doi>`; an entry located by a :ref:`url <guide-project-citations-url>` cannot set it.
Only one entry can make the claim, since a site is the landing page of one DOI.
A ``self`` entry is also the site's :ref:`preferred <guide-project-citations-preferred>` citation unless another entry claims that, which is why the configuration above never writes ``preferred``: the dataset is both the DOI this site lands and the citation it asks for.

What the claim does
===================

Every page of the site, not only the home page, carries the ``self`` citation in its ``<head>`` as Highwire and Dublin Core meta tags and as the subject of a schema.org JSON-LD block (see :ref:`guide-citation-metadata`).
Highwire tags are what Google Scholar indexes and what Zotero's embedded-metadata translator reads, so a reader who lands on any page of the site gets a one-click "Save to Zotero" with the right title, creators, date, and DOI.
The JSON-LD block is what makes a ``type = "dataset"`` release indexable by Google Dataset Search.

The visible surfaces follow.
The :ref:`site footer <guide-footer-citations>` shows the citation on every page, so the page a reader arrives at is a landing page whether or not it carries a card:

.. code-block:: text

   How to cite

   DATASET

   NSF-DOE Vera C. Rubin Observatory (2025). Data Preview 2. NSF-DOE
   Vera C. Rubin Observatory. https://doi.org/10.71929/rubin/2570308

   To be used when citing the DP2 dataset and this documentation.

A :ref:`citation card <guide-citation-card>` with no argument renders the same citation wherever a page asks for one, for a "Citing this release" page or a section of the home page:

.. code-block:: rst

   .. citation-card::

.. code-block:: text

   DATASET

   NSF-DOE Vera C. Rubin Observatory (2025). Data Preview 2. NSF-DOE
   Vera C. Rubin Observatory. https://doi.org/10.71929/rubin/2570308

   To be used when citing the DP2 dataset and this documentation.

Both end in the DOI as a resolvable ``https://doi.org/`` link, and both carry the BibTeX entry composed from the same fields, which is the form the DataCite and Crossref display guidelines ask for.
The ``Paper`` entry, which is neither ``self`` nor ``preferred``, reaches no surface on its own; a page shows it with ``.. citation-card:: Paper`` or links it with the :ref:`doi role <guide-citation-doi-role>`.

Asking readers to cite something else
=====================================

A site can also set ``self`` and ``preferred`` on *different* entries, which is the site published with a DOI of its own that nonetheless asks readers to cite something else, such as the paper that describes the release.
The :ref:`footer <guide-footer-citations>` then shows both by default, because a landing page owes its reader the citation of the DOI it is the landing page of whether or not that is the citation it asks for.
Such a site shows one of them instead by writing :ref:`in_footer = false <guide-project-citations-in-footer>` on the other.

A site whose own work is published somewhere else, or has never been deposited for a DOI, is not a landing page at all and marks nothing ``self``; see :doc:`cff` and :doc:`url-only`.
A site that is the landing page of several DOIs, one per data product, claims a page of the site for each; see :doc:`site-pages`.
