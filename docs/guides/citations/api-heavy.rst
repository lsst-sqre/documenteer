.. _guide-citation-api-heavy:

################################
Sites with a large API reference
################################

A package guide is mostly generated API pages, and a footer citation appears under every one of them.
That's the right default for a data release, whose pages a reader arrives at from a DOI.
It's noise on a site where a hundred pages document one function each.

Such a site sets :ref:`in_footer = false <guide-project-citations-in-footer>` on its :ref:`preferred <guide-project-citations-preferred>` entry and shows the citation once, on the page where a reader would look for it:

.. code-block:: toml

   [[project.citations]]
   url = "https://github.com/lsst-sqre/safir"
   type = "software"
   label = "Safir"
   preferred = true
   in_footer = false
   title = "Safir"
   authors = [{ name = "NSF-DOE Vera C. Rubin Observatory" }]

.. code-block:: rst

   .. citation-card::

That entry states no :ref:`version <guide-project-citations-version>` either, so it's cited with the site's own version.
On a site published from ``main`` that's a development build (see :ref:`what a site published from a branch cites <guide-citation-development-versions>`).

Removing the citation from the footer loses nothing else.
``in_footer`` governs only the visible surfaces: the preferred citation is still described in full in the :ref:`site-wide JSON-LD block <guide-citation-metadata>` that every page of the site carries, so a crawler finds it on whichever page it lands, and a reader who arrives at the home page sees the card.
The BibTeX copy script loads only on pages that have a copy button, so only the page with the card loads it.
