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
     - :file:`technote.toml` conforms to the technote schema. A schema failure skips only the author checks (``TN1xx``), which need the parsed metadata; the requirements and content checks still run. When the failure comes from a historical author name form, the finding names that form and points at :command:`documenteer technote migrate`.
     - Error
   * - ``TN002``
     - Structural
     - :file:`requirements.txt` declares ``documenteer`` with the ``[technote]`` extra.
     - Warning
   * - ``TN003``
     - Structural
     - :file:`requirements.txt` does not pin Sphinx as a separate requirement (``documenteer[technote]`` already constrains it).
     - Warning
   * - ``TN004``
     - Structural
     - :file:`technote.toml` exists in the technote directory. A missing file short-circuits the remaining checks, since the directory is not a technote.
     - Error
   * - ``TN005``
     - Structural
     - :file:`technote.toml` is syntactically valid TOML. A syntax error skips only the author checks (``TN1xx``), like ``TN001``.
     - Error
   * - ``TN006``
     - Structural
     - The technote has a content file (:file:`index.rst`, :file:`index.md`, or :file:`index.ipynb`). Checked only for Sphinx technotes; a directory with no content file *and* no :file:`conf.py` is treated as a non-Sphinx technote instead (see below).
     - Error
   * - ``TN101``
     - Metadata
     - Every author declares an ``internal_id``. The finding suggests the likely ID when the author can be matched in the author database (see :ref:`technote-validate-suggested-ids`).
     - Error
   * - ``TN102``
     - Metadata
     - Each author's ``internal_id`` resolves in the Rubin author database (`authordb.yaml`_). Also fires when the database returns a malformed record for the ID. The finding suggests the likely ID when the author can be matched by name or ORCID (see :ref:`technote-validate-suggested-ids`).
     - Error
   * - ``TN103``
     - Metadata
     - The author database is reachable so that IDs can be resolved. Fires only for a transport failure (connection error, timeout, or a non-404 HTTP status); a malformed record is reported as ``TN102`` instead.
     - Warning
   * - ``TN201``
     - Content
     - The content file declares an abstract directive. A technote with no content file at all is reported as ``TN006`` instead, and a directive that is present but empty as ``TN204``.
     - Error
   * - ``TN202``
     - Content
     - The abstract uses the abstract directive rather than an ordinary ``Abstract`` section heading. The finding locates the heading as ``file:line``.
     - Error
   * - ``TN203``
     - Content
     - The content file can be parsed to scan for an abstract (an :file:`index.ipynb` notebook is valid JSON).
     - Error
   * - ``TN204``
     - Content
     - The abstract directive has body content. Most often the abstract text was left unindented under ``.. abstract::``, which reStructuredText reads as an empty directive: the page publishes an empty abstract section and an empty ``og:description``. The finding locates the directive marker as ``file:line``.
     - Error

.. _technote-validate-suggested-ids:

Suggested author IDs
====================

An author ``internal_id`` that is missing (``TN101``) or unknown (``TN102``) is a dead end on its own, so the validator tries to name the ID you probably want.
It searches the author database for the author's name and appends a suggestion when exactly one entry matches confidently:

.. code-block:: text

   [TN101] Author Yusra AlSayyad is missing an internal_id. Did you mean 'alsayyady' (matched by ORCID)? Run 'documenteer technote sync-authors' after adding it.
   [TN102] Author Lynne Jones has internal_id 'lynnej', which is not in the author database. Did you mean 'jonesrl' (R. Lynne Jones, matched by name)?

The message states what the match is based on:

- **matched by ORCID** — the ``orcid`` in your :file:`technote.toml` author entry is the same as that entry's ORCID. This is the strongest evidence, and holds even when the two spell the name differently.
- **matched by name** — a single near-exact name match, whose ORCID (if it has one) does not contradict yours.

The suggestion is deliberately conservative and best-effort: an ambiguous search (several equally good matches, as a common family name gives) or a match contradicted by a differing ORCID adds nothing to the message, and a failed lookup leaves the finding exactly as it would otherwise read.
A suggestion never changes whether the command passes or fails — verify it before you use it.

How the abstract is found
=========================

The abstract check is a source scan, not a Sphinx build, so it is worth knowing what it does and does not see.

- Both the reStructuredText directive (``.. abstract::``) and the MyST fenced directive (a triple-backtick or ``:::`` fence opening with ``{abstract}``) are recognized, in any letter case — docutils lowercases directive names, so a ``{Abstract}`` fence builds and passes.
- In reStructuredText, text on the marker line itself (``.. abstract:: The abstract.``) is directive content and passes.
- Directive *options* (for example ``:class: dropdown``) are configuration rather than content, so a directive holding only options is empty (``TN204``).
- An abstract factored into another file and pulled in with ``.. include::`` or a MyST ``{include}`` fence is found: those includes are resolved one level deep, relative to the content file. Includes within an included file are not followed, and an include that is missing or points outside the technote directory is ignored (Sphinx reports those itself).
- An :file:`index.ipynb` notebook's markdown cells are concatenated before scanning, so its findings name the file without a line number.

Non-Sphinx technotes
====================

Some technote-series repositories are not Sphinx projects at all: they publish through the shared technote CI with a custom build command (an Org-mode deck, for example).
When a directory has no content file (:file:`index.rst`, :file:`index.md`, or :file:`index.ipynb`) *and* no :file:`conf.py`, the validator treats it as one of these and checks only that its :file:`technote.toml` is well formed — ``TN004``, ``TN005``, ``TN001``, and the author checks (``TN1xx``).
The :file:`requirements.txt` checks (``TN002``/``TN003``), the content checks (``TN2xx``), and ``TN006`` are skipped, since they describe a Documenteer/Sphinx build that these repositories do not have.
A repository that *does* have a :file:`conf.py` but no content file is a broken Sphinx technote, and is reported as ``TN006``.

.. note::

   Author ``internal_id`` values are the key to consistent author identification across Rubin documents, and a missing or unknown ID blocks DOI generation.
   See :doc:`author-metadata` to learn how to add and update the authors that ``TN101``–``TN103`` check.

Related documentation
=====================

- :doc:`author-metadata` — add and update the authors that the ``TN1xx`` checks validate.
- :doc:`migrate` — the migration tool sets up the :file:`Makefile`, :file:`requirements.txt`, and abstract directive that these checks rely on.
