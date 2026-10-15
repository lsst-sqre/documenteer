.. _guide-citations:

#########
Citations
#########

Your documentation can help readers reference your project by including citation information.
A site can carry several citations: the DOI the site itself is published under, a paper that describes the work, and the software the site documents.
Documenteer displays those citations in four places:

- As :ref:`machine-readable metadata <guide-citation-metadata>` in every page's HTML ``<head>``, which is what makes a site a DOI's landing page
- In the :ref:`site footer <guide-footer-citations>`, so a reader finds the citation from any page of the site
- In :ref:`citation cards <guide-citation-card>` placed in your content, on a DOI landing page or on a page about citing the project
- As :ref:`inline DOI links <guide-citation-doi-role>`, wherever a sentence, a bullet, or a table cell refers to one of the works

All four read the same declared citations, so they never disagree about how the site asks to be cited.
The rest of this page shows the basics: how to declare a citation, and where it appears.
The recipes that follow cover specific kinds of site, and the display pages go into each surface in depth.

Declaring a citation
====================

A site declares its citations in the :ref:`[[project.citations]] <guide-project-citations>` array of :file:`documenteer.toml`, one entry per work.
An entry is made of three kinds of field:

- **Bibliographic fields** that compose the citation: :ref:`title <guide-project-citations-title>`, :ref:`authors <guide-project-citations-authors>`, :ref:`publisher <guide-project-citations-publisher>`, :ref:`date <guide-project-citations-date>`, :ref:`type <guide-project-citations-type>`, and :ref:`version <guide-project-citations-version>`.
  An entry can state them itself, or read them from a repository's :file:`CITATION.cff` file with :ref:`cff <guide-project-citations-cff>`.
- **A locator**, either a :ref:`doi <guide-project-citations-doi>` or a :ref:`url <guide-project-citations-url>`, which the rendered citation ends in as a link.
- **Presentation fields** that say how the site uses the entry: :ref:`label <guide-project-citations-label>`, :ref:`note <guide-project-citations-note>`, :ref:`self <guide-project-citations-self>`, :ref:`preferred <guide-project-citations-preferred>`, :ref:`in_footer <guide-project-citations-in-footer>`, :ref:`page <guide-project-citations-page>`, and :ref:`bibtex_key <guide-project-citations-bibtex-key>`.

This site declares two citations, and every card, link, and footer citation on this page is rendered from them:

.. code-block:: toml
   :caption: docs/documenteer.toml

   [[project.citations]]
   cff = "../CITATION.cff"
   label = "Software"
   preferred = true
   note = "Cite the version of Documenteer you used; this site documents the version shown."

   [[project.citations]]
   doi = "10.26624/XWGH8202"
   label = "Paper"
   type = "article"
   bibtex_key = "2025ASPC..541..151S"
   in_footer = false
   title = "The Documentation Developer Experience: Documentation Engineering at the Vera C. Rubin Observatory"
   publisher = "Astronomical Society of the Pacific"
   date = 2025
   authors = [
       { family_name = "Sick", given_name = "Jonathan", orcid = "https://orcid.org/0000-0003-3001-676X", affiliation = "Vera C. Rubin Observatory" },
       { family_name = "Economou", given_name = "Frossie", affiliation = "Vera C. Rubin Observatory" },
   ]
   note = "Cite this paper when describing how Rubin Observatory builds its documentation."

The first entry reads Documenteer's own :file:`CITATION.cff` file at the root of its repository, a software record with no DOI, and marks it as the citation the site prefers.
The second states the fields of a conference paper itself, located by its DOI, and keeps the paper out of the footer so that a card or an inline link is the only place it shows.
The :ref:`field reference <guide-project-citations>` describes every field; the recipes below show which fields each kind of site needs.

.. _guide-citations-self-preferred:

self and preferred
==================

Two of the presentation fields answer two different questions, and it is worth keeping them apart:

:ref:`self <guide-project-citations-self>`
    Whether this site is the DOI's registered *landing page*: whether doi.org sends a reader here.
    It alone drives the machine-readable metadata in each page's ``<head>``, and it needs a DOI to be the landing page of.

:ref:`preferred <guide-project-citations-preferred>`
    Which citation the site asks readers to *use*.
    It is what a card with no argument renders, and the citation the footer shows.

A site's citations take one of three shapes:

**self alone**
    A site published with a DOI of its own, such as a data release's documentation, marks that entry ``self``.
    The entry is the preferred citation too unless another entry claims that, so such a site never needs to think about the difference.
    See :doc:`doi-landing-page`.

**preferred alone**
    A site whose citation is a work published somewhere else, or software that has never been deposited for a DOI, marks the citation it asks for ``preferred`` and marks nothing ``self``, because no page of it is any DOI's landing page.
    This is the shape of this site.
    See :doc:`cff` and :doc:`url-only`.

**Both, on different entries**
    A site published with a DOI of its own that nonetheless asks readers to cite something else.
    The footer then shows both by default; see :doc:`footer`.

Where citations are displayed
=============================

Site footer
-----------

Scroll to the bottom of this page.
The footer opens with a "How to cite" heading and the site's :ref:`preferred <guide-project-citations-preferred>` citation, and it does the same on every page of the site.
By default the footer shows the preferred entry, the ``self`` entry, and any entry that sets :ref:`in_footer = true <guide-project-citations-in-footer>`.
This site's footer shows only the software, because the paper's entry sets ``in_footer = false``.
See :doc:`footer`.

Citation cards
--------------

The ``citation-card`` directive renders a citation as a card wherever a page asks for one.
With no argument it renders the preferred citation:

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

.. citation-card::

An argument selects another of the site's entries by its label, its BibTeX key, or its DOI:

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

.. citation-card:: Paper

The paper is kept out of this site's footer, so a card or an inline link is the only way a page shows it.
See :doc:`cards`.

Inline DOI links
----------------

The ``doi`` role links a declared citation's DOI inline, with the resolvable ``https://doi.org/`` URL as the link text: the paper is published as :doi:`Paper`, written as ``:doi:`Paper```.
See :doc:`doi-role`.

Machine-readable metadata
-------------------------

Every page of a site that marks an entry ``self`` carries that citation in its ``<head>`` as Highwire and Dublin Core meta tags, which is what Google Scholar and Zotero read.
This site marks no entry ``self``, so it emits none of those tags.
Every page does carry a schema.org JSON-LD block describing the site, with the software under ``citation``; view the source of this page to see it.
See :doc:`metadata`.

Details and recipes
===================

.. toctree::
   :maxdepth: 1
   :caption: Recipes

   doi-landing-page
   site-pages
   cff
   url-only
   api-heavy

.. toctree::
   :maxdepth: 1
   :caption: Displaying citations

   cards
   doi-role
   footer
   metadata
   troubleshooting
