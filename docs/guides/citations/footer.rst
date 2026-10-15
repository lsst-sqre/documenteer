.. _guide-footer-citations:

################
Footer citations
################

The site footer shows the citations on every page, which is what makes each page of the guide a landing page for the site's DOI rather than only the page that carries a card.
They open the footer, above the horizontal rule that separates them from the Rubin Observatory links, copyright, and funding statement every guide shares: those are the same everywhere, and the citations are this site's own.

The footer shows the site's :ref:`preferred <guide-project-citations-preferred>` citation, its :ref:`self <guide-project-citations-self>` entry, and every entry that sets :ref:`in_footer = true <guide-project-citations-in-footer>`, in the order :file:`documenteer.toml` declares them.
The first two are one entry on a site that publishes its own DOI, so such a site shows one citation.
A site that separates them shows both, and writes :ref:`in_footer = false <guide-project-citations-in-footer>` on one to show only the other.
Each one shows the same three parts a card does — the :ref:`label <guide-project-citations-label>`, the citation with its DOI as a ``https://doi.org/`` hyperlink, and the :ref:`note <guide-project-citations-note>` — under a "How to cite" heading.

Scroll to the bottom of this page to see it.
This site :ref:`declares two citations <guide-citations>`, and its footer shows one of them: the Software entry, which is the preferred citation.
The Paper entry writes ``in_footer = false``, so the footer leaves it out and a :ref:`card <guide-citation-card>` or a :ref:`doi role <guide-citation-doi-role>` is the only place it shows.
Deleting that line would put the paper in the footer of every page beside the software.

Each entry also carries the same collapsed ``BibTeX`` disclosure and ``Copy BibTeX`` button a :ref:`card <guide-citation-card>` does, so a reader can take the entry from whichever surface they are looking at.

A guide that declares no citations, and one whose entries all set ``in_footer = false``, renders no citations block at all.
The script behind the copy buttons is referenced by the pages that have one — every page of a site whose footer shows a citation, and otherwise the pages that carry a :ref:`card <guide-citation-card>` — so a guide that displays no citation loads nothing.
A site whose pages are mostly generated API reference may prefer no footer citation at all; see :doc:`api-heavy`.
