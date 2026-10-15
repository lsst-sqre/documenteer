.. _guide-citation-api-heavy:

################################
Sites with a large API reference
################################

A package guide is mostly generated API pages, and a footer citation appears under every one of them.
That is the right default for a data release, whose pages a reader arrives at from a DOI; it is noise on a site where a hundred pages document one function each.

Such a site writes :ref:`in_footer = false <guide-project-citations-in-footer>` on its :ref:`preferred <guide-project-citations-preferred>` entry and shows the citation once, on the page a reader looking for it would visit:

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

That entry states no :ref:`version <guide-project-citations-version>` either, so it is cited at the site's own — a development build on a site published from ``main``, which is :ref:`what a site published from a branch cites <guide-citation-development-versions>`.

Nothing is lost by silencing the footer.
``in_footer`` governs the visible surfaces alone: the preferred citation is still described in full in the :ref:`site-wide JSON-LD block <guide-citation-metadata>` that every page of the site carries, so a crawler finds it wherever it lands, and a reader who arrives at the home page meets the card.
The copy script follows the button, so only the page with the card loads it.
