.. _guide-citation-url-only:

######################################
Software that has never been deposited
######################################

Most packages carry no DOI at all.
Releasing to PyPI and tagging on GitHub mints none, and a library that has never been deposited with Zenodo or DataCite has nothing a ``https://doi.org/`` link could resolve to.
Such a work is cited by *where it lives* instead — a :ref:`url <guide-project-citations-url>` in place of a :ref:`doi <guide-project-citations-doi>` — which is the shape a repository's :file:`CITATION.cff` file already takes, and which a site that keeps no such file states in :file:`documenteer.toml` directly:

.. code-block:: toml

   # documenteer.toml

   [[project.citations]]
   url = "https://github.com/lsst-sqre/safir"
   label = "Software"
   type = "software"
   preferred = true
   title = "Safir"
   publisher = "NSF-DOE Vera C. Rubin Observatory"
   date = 2020
   authors = [
       { name = "NSF-DOE Vera C. Rubin Observatory", ror = "https://ror.org/048g3cy84" },
   ]

The entry is marked :ref:`preferred <guide-project-citations-preferred>`, and a citation with no DOI always is: :ref:`self <guide-project-citations-self>` is the claim that this site is a DOI's registered *landing page*, so it needs a DOI to be the landing page of, while ``preferred`` only says which citation the site asks readers to use.
Marking neither is what leaves a site with nothing on its surfaces — the footer shows no citation, and a :ref:`card <guide-citation-card>` with no argument has none to render and warns (see :ref:`guide-unresolvable-citations`) — so a package site's single entry sets ``preferred``.

Nothing else about the entry is special.
The :ref:`footer <guide-footer-citations>` and a :ref:`card <guide-citation-card>` render it the way they render a cited DOI, ending in a link to the repository rather than to doi.org, and it reaches the site-wide JSON-LD block in full as the work the site asks to be cited.
The one surface it cannot reach is the inline :ref:`doi role <guide-citation-doi-role>`, whose link *text* is the DOI: an entry that has none is linked with ordinary hyperlink syntax instead.
Nor does such a site carry the per-page citation meta tags, which describe a DOI's landing page and are emitted only for a :ref:`self <guide-project-citations-self>` entry; see :ref:`guide-citation-metadata`.

.. _guide-citation-development-versions:

The entry states no :ref:`version <guide-project-citations-version>` and is cited with one anyway.
A ``software`` entry the site marks :ref:`preferred <guide-project-citations-preferred>` *is* this site's own package, so it takes the site's :ref:`project.version <guide-project-version>`, and on a site published from its default branch — as `safir.lsst.io <https://safir.lsst.io>`__ is, from ``main`` — that is the development build the documentation was made from: ``Safir (version 15.2.2.dev4+g9c8d32d17).``
That is deliberate.
These pages document that code and not the last tag, and naming the tag would credit a release the reader is not reading the documentation of.

A site that would rather cite releases has two ways to say so.
Setting :ref:`version <guide-project-citations-version>` on the entry pins it, and always wins over the default.
Publishing the documentation from tags instead of from the default branch makes the version the site builds with a release, which leaves the entry stating nothing and citing ``15.2.2`` — and is the honest form of the request, since the published pages are then the release's documentation.

A site whose repository keeps a :file:`CITATION.cff` file does not restate any of this: :ref:`cff <guide-project-citations-cff>` takes the URL from the file's ``url``, or from its ``repository-code`` when the file names no landing page, along with the rest of the record.
That is how this site cites Documenteer; see :doc:`cff`.
