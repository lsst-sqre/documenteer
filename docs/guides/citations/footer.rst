.. _guide-footer-citations:

################
Footer citations
################

The site footer shows the site's citations on every page, which makes every page of the guide a landing page for the site's DOI, not only the pages that carry a card.
The citations open the footer, above the horizontal rule that separates them from the Rubin Observatory links, copyright, and funding statement that every guide shares.

The footer shows the site's :ref:`preferred <guide-project-citations-preferred>` citation, its :ref:`self <guide-project-citations-self>` entry, and every entry that sets :ref:`in_footer = true <guide-project-citations-in-footer>`, in the order :file:`documenteer.toml` declares them.
On a site that publishes its own DOI, the first two are usually the same entry, so the footer shows one citation.
A site that sets them on different entries shows both, and can set :ref:`in_footer = false <guide-project-citations-in-footer>` on one to show only the other.
Under a "How to cite" heading, each citation shows the same three parts a card does: the :ref:`label <guide-project-citations-label>`, the citation with its DOI as a ``https://doi.org/`` hyperlink, and the :ref:`note <guide-project-citations-note>`.

Scroll to the bottom of this page to see it.
This site :ref:`declares two citations <guide-citations>`, and its footer shows one of them: the Software entry, which is the preferred citation.
The Paper entry is neither preferred nor ``self``, so the footer leaves it out, and a :ref:`card <guide-citation-card>` or a :ref:`doi role <guide-citation-doi-role>` is the only place it shows.
Its ``in_footer = false`` only states that default explicitly.
Setting ``in_footer = true`` instead would put the paper in the footer of every page beside the software.

Each entry also carries the same collapsed ``BibTeX`` disclosure and ``Copy BibTeX`` button a :ref:`card <guide-citation-card>` does, so a reader can take the entry from whichever surface they are looking at.

A guide that declares no citations, or whose entries all set ``in_footer = false``, renders no citations block at all.
The script behind the copy buttons loads only on pages that have a button: every page of a site whose footer shows a citation, and otherwise only the pages that carry a :ref:`card <guide-citation-card>`.
A guide that displays no citation loads nothing.
A site whose pages are mostly generated API reference may prefer no footer citation at all.
See :doc:`api-heavy`.
