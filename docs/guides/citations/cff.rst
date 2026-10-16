.. _guide-citation-cff:

#################################
Citing software from CITATION.cff
#################################

A repository that keeps a :file:`CITATION.cff` file already states how its software should be cited, and GitHub's "Cite this repository" button reads the same file.
A guide for that repository reads it too, with :ref:`cff <guide-project-citations-cff>`, rather than restating the title, authors, and location in :file:`documenteer.toml`.
The path is resolved relative to :file:`documenteer.toml`, so a file at the repository root is ``../CITATION.cff`` from a :file:`docs/` directory.

A file that describes the software alone
========================================

Documenteer's own repository is the simplest case.
Its :file:`CITATION.cff` holds one record, which describes the package, and no ``preferred-citation``:

.. code-block:: yaml
   :caption: CITATION.cff

   cff-version: 1.2.0
   message: If you use Documenteer, please cite it using the metadata from this file.
   type: software
   title: Documenteer
   authors:
     - family-names: Sick
       given-names: Jonathan
       orcid: https://orcid.org/0000-0003-3001-676X
       affiliation: Vera C. Rubin Observatory
   repository-code: https://github.com/lsst-sqre/documenteer
   url: https://documenteer.lsst.io
   license: MIT

This site's entry for it names the file, a label, and a note, and marks the citation :ref:`preferred <guide-project-citations-preferred>`:

.. code-block:: toml
   :caption: docs/documenteer.toml

   [[project.citations]]
   cff = "../CITATION.cff"
   label = "Software"
   preferred = true
   note = "Cite the version of Documenteer you used; this site documents the version shown."

It is ``preferred`` rather than :ref:`self <guide-project-citations-self>` because the software has no DOI: ``self`` is the claim that this site is a DOI's registered landing page, so it needs a DOI to be the landing page of, while ``preferred`` only says which citation the site asks readers to use (see :doc:`url-only`).
The card below is rendered from that entry:

.. citation-card::

Three things about that card come from reading the file's top-level record:

- **The location** is the file's ``url``, this site, rather than its ``repository-code``.
  A file that names a landing page is cited at it, and the repository only when the file names no landing page.
- **The version** is the one this build of the documentation was made from, although neither the file nor the entry states one.
  An entry reading a repository's own record describes this site's own package, so it takes the file's ``version`` when the file states one and the site's own :ref:`project.version <guide-project-version>` otherwise.
- **The missing date** is not reported.
  Software located by where it lives, rather than by a DOI, has no publication event to date, so an entry reading a file's top-level record is exempt from the :ref:`undated-citation warning <guide-undated-citations>`.

The entry states no :ref:`type <guide-project-citations-type>` either, and does not need to: a top-level record that declares none is read as ``software``, the default CFF defines for that key, so the citation composes as ``@software`` and publishes as a `SoftwareSourceCode <https://schema.org/SoftwareSourceCode>`__.

A file that prefers a paper
===========================

Many repositories ask to be cited by a paper that describes them, and say so with a ``preferred-citation`` record in the same file.
That paper's landing page is its publisher's, so the site marks it ``preferred`` and marks nothing ``self``:

.. code-block:: toml

   # documenteer.toml

   [[project.citations]]
   cff = "../CITATION.cff"
   label = "Paper"
   preferred = true
   note = "Cite this paper in publications that use the package."

An entry reads the file's ``preferred-citation`` by default, which is what GitHub's button reads, and falls back to the top-level record when the file has none, which is how the Documenteer entry above got its software record without saying so.
The site then displays that citation everywhere it displays one, while no page of it claims to be the paper's landing page.
Setting :ref:`self <guide-project-citations-self>` on that entry instead is an error the build reports, since it would publish every page of the site as the paper's full text, a claim only the paper's publisher can make.

Such a repository is often worth citing twice: the paper for the work, and the package for the code that was run.
A second entry against the same file, with :ref:`cff_preferred = false <guide-project-citations-cff-preferred>`, reads the file's top-level record rather than its preferred citation:

.. code-block:: toml

   # documenteer.toml

   [[project.citations]]
   cff = "../CITATION.cff"
   cff_preferred = false
   label = "Software"
   in_footer = true
   note = "Cite the version you ran; this page names the version it documents."

The package is cited by where it lives: the file's ``url``, or its ``repository-code`` when it names no landing page.
Writing :ref:`in_footer = true <guide-project-citations-in-footer>` puts it in the footer beside the preferred paper, so a reader meets both.

Versions and dates
==================

The software entry states no :ref:`version <guide-project-citations-version>`, and gets one anyway, because an entry reading a repository's own record describes this site's own package.
Against a :file:`CITATION.cff` for ``safir``, released in 2020 and documented at 12.3.0, the entry renders:

.. code-block:: text

   SOFTWARE

   NSF-DOE Vera C. Rubin Observatory (2020). Safir (version 12.3.0).
   https://github.com/lsst-sqre/safir

   Cite the version you ran; this page names the version it documents.

That release is what a software citation exists to carry, which is why the note is written around it rather than around the year.
Software released continuously has no publication date to speak of.
Its :ref:`date <guide-project-citations-date>` is conventionally the year of its first release, which is defensible precisely because it never moves — every later release cites the same way, so a reader's bibliography does not churn — but it is not what identifies the code that ran.
The version is.
That is also why an entry like this one — software located by its repository, stating no date — is not reported as :ref:`undated <guide-undated-citations>`.
A ``preferred-citation`` record is a different matter: it names a work other than the repository, and an undated one is reported like any other work.

A file's ``date-released`` dates the top-level record, and a ``preferred-citation`` carries its own ``year`` or ``date-published``; an entry that reads one record never takes the other's date.
A site that wants a dated software citation writes the date in the record the entry reads, or on the entry itself with :ref:`date <guide-project-citations-date>`, which beats the file.
