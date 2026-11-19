.. _guide-citation-url-only:

######################################
Software that has never been deposited
######################################

Most packages carry no DOI at all.
Releasing to PyPI and tagging on GitHub don't mint one, and a library that has never been deposited with Zenodo or DataCite has nothing a ``https://doi.org/`` link could resolve to.
Such a work is cited by *where it lives* instead, with a :ref:`url <guide-project-citations-url>` in place of a :ref:`doi <guide-project-citations-doi>`.
A repository's :file:`CITATION.cff` file already works this way, and a site without one states the same information directly in :file:`documenteer.toml`:

.. code-block:: toml
   :caption: documenteer.toml

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

The entry is marked :ref:`preferred <guide-project-citations-preferred>` rather than :ref:`self <guide-project-citations-self>`, as any citation without a DOI must be.
``self`` claims that this site is a DOI's registered *landing page*, so it requires a DOI, while ``preferred`` only says which citation the site asks readers to use.
With neither set, the site displays no citation by default: the footer shows none, and a :ref:`card <guide-citation-card>` with no argument has nothing to render and warns (see :ref:`guide-unresolvable-citations`).
A package site's single entry therefore sets ``preferred``.

Nothing else about the entry is special.
The :ref:`footer <guide-footer-citations>` and a :ref:`card <guide-citation-card>` render it the way they render a work with a DOI, ending in a link to the repository rather than to doi.org, and the site-wide JSON-LD block describes it in full as the work the site asks readers to cite.
The one surface that can't show it is the inline :ref:`doi role <guide-citation-doi-role>`, whose link *text* is the DOI.
Link an entry without a DOI using ordinary hyperlink syntax instead.
Such a site also doesn't carry the per-page citation meta tags, which describe a DOI's landing page and are emitted only for a :ref:`self <guide-project-citations-self>` entry.
See :ref:`guide-citation-metadata`.

.. _guide-citation-development-versions:

The entry states no :ref:`version <guide-project-citations-version>` but is cited with one anyway.
A :ref:`software <guide-project-citations-type>` entry that the site marks :ref:`preferred <guide-project-citations-preferred>` describes the site's own package, so it takes the site's :ref:`project.version <guide-project-version>`.
On a site published from its default branch, as `safir.lsst.io <https://safir.lsst.io>`__ is from ``main``, that version is the development build the documentation was made from: ``Safir (version 15.2.2.dev4+g9c8d32d17).``
That's deliberate.
The pages document that code rather than the last tag, and naming the tag would cite a release that the reader isn't reading the documentation for.

A site that would rather cite releases has two options.
Setting :ref:`version <guide-project-citations-version>` on the entry pins it, and always takes precedence over the default.
Publishing the documentation from tags instead of from the default branch makes the site's build version a release, so the entry states nothing and still cites ``15.2.2``.
The second option is the more accurate one, since the published pages are then the release's documentation.

A site whose repository keeps a :file:`CITATION.cff` file doesn't need to restate any of this: :ref:`cff <guide-project-citations-cff>` takes the URL from the file's ``url``, or from its ``repository-code`` when the file names no landing page, along with the rest of the record.
That's how this site cites Documenteer.
See :doc:`cff`.
