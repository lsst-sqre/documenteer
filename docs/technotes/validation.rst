:og:description: Documenteer's "technote validate" command checks a technote's metadata and structure — author IDs, the abstract, and requirements — before it is built and published.

###################
Validate a technote
###################

Documenteer provides a command-line tool, :command:`documenteer technote validate`, that checks a technote's metadata and structure before it is built and published.
Its most important job is verifying that every author has an ``internal_id`` that resolves in the Rubin author database (`authordb.yaml`_), since these IDs are needed to mint a DOI for the technote.
The command also checks that the content declares an abstract and that :file:`requirements.txt` installs Documenteer correctly.

Rubin's technote CI (from the `rubin-sphinx-technote-workflows <https://github.com/lsst-sqre/rubin-sphinx-technote-workflows>`__ repository) runs this command so that builds fail early when a technote's metadata is incomplete.

Run the validator
=================

Run the validator from the root of a technote repository:

.. prompt:: bash

   documenteer technote validate

If your technote uses the standard :file:`Makefile` (see :doc:`migrate`), you can equivalently run:

.. prompt:: bash

   make validate

The command prints each issue it finds, prefixed with its stable code (for example, ``[TN101]``), followed by a summary.
It exits with a non-zero status when any *error*-level issue remains, which is what causes a CI build to fail.
*Warning*-level issues are reported but do not fail the command unless you pass ``--strict``.

Options
=======

``--dir <path>``, ``-d <path>``
    Path to the technote directory to validate.
    Defaults to the current directory (``.``).
    The command locates :file:`technote.toml`, the content file (:file:`index.rst`, :file:`index.md`, or :file:`index.ipynb`), and :file:`requirements.txt` within this directory.

``--strict``, ``-s``
    Promote all warnings to errors.
    With this flag, any finding — including the warning-level checks below — causes the command to exit non-zero.

Checks
======

Each check has a stable, linter-style code so that findings are easy to triage (and, in the future, to except individually).
Codes are grouped by concern: ``TN0xx`` for structural checks, ``TN1xx`` for metadata, and ``TN2xx`` for content.

.. list-table:: Technote validation checks
   :header-rows: 1
   :widths: 12 15 53 20

   * - Code
     - Group
     - Description
     - Default severity
   * - ``TN001``
     - Structural
     - :file:`technote.toml` conforms to the technote schema. A schema failure short-circuits the remaining checks.
     - Error
   * - ``TN002``
     - Structural
     - :file:`requirements.txt` declares ``documenteer`` with the ``[technote]`` extra.
     - Warning
   * - ``TN003``
     - Structural
     - :file:`requirements.txt` does not pin Sphinx as a separate requirement (``documenteer[technote]`` already constrains it).
     - Warning
   * - ``TN101``
     - Metadata
     - Every author declares an ``internal_id``.
     - Error
   * - ``TN102``
     - Metadata
     - Each author's ``internal_id`` resolves in the Rubin author database (`authordb.yaml`_).
     - Error
   * - ``TN103``
     - Metadata
     - The author database is reachable so that IDs can be resolved.
     - Warning
   * - ``TN201``
     - Content
     - The content declares a non-empty abstract.
     - Error
   * - ``TN202``
     - Content
     - The abstract uses the ``.. abstract::`` directive rather than an ordinary ``Abstract`` section heading.
     - Error

.. note::

   Author ``internal_id`` values are the key to consistent author identification across Rubin documents, and a missing or unknown ID blocks DOI generation.
   See :doc:`author-metadata` to learn how to add and update the authors that ``TN101``–``TN103`` check.

Related documentation
=====================

- :doc:`author-metadata` — add and update the authors that the ``TN1xx`` checks validate.
- :doc:`migrate` — the migration tool sets up the :file:`Makefile`, :file:`requirements.txt`, and abstract directive that these checks rely on.
