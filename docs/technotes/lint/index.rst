:og:description: Documenteer's "technote lint" command checks a technote's metadata and structure — author IDs, citation metadata, the abstract, and requirements — before it is built and published.

.. _technote-lint:

###############
Lint a technote
###############

Documenteer provides a command-line linter, :command:`documenteer technote lint`, that checks a technote's metadata and structure before it is built and published.
Its most important job is verifying that every author has an ``internal_id`` that resolves in the Rubin author database (`authordb.yaml`_), since these IDs are needed to mint a DOI for the technote.
The command also checks that the content declares an abstract, that :file:`requirements.txt` installs Documenteer correctly, and that the technote's citation metadata — its DOI, the metadata registered for that DOI with DataCite, and, where the repository has adopted one, its :file:`CITATION.cff` — is in order.

Rubin's technote CI (from the `rubin-sphinx-technote-workflows <https://github.com/lsst-sqre/rubin-sphinx-technote-workflows>`__ repository) runs this command so that builds fail early when a technote's metadata is incomplete.

Run the linter
==============

Run the linter from the root of a technote repository:

.. prompt:: bash

   documenteer technote lint

If your technote uses the standard :file:`Makefile` (see :doc:`../migrate`), the linter also runs as part of the repository's combined lint target, alongside the Pre-commit hooks and the link checker:

.. prompt:: bash

   make lint

The command prints each issue it finds, prefixed with its stable rule code (for example, ``[TN101]``), followed by a summary and a link to the documentation page for every rule that fired:

.. code-block:: text

   [TN101] Author Yusra AlSayyad is missing an internal_id. Did you mean 'alsayyady' (matched by ORCID)? Run 'documenteer technote sync-authors' to add it.
   Found 1 error(s) and 0 warning(s).
   Learn more:
     TN101: https://documenteer.lsst.io/technotes/lint/tn101.html

The command exits with a non-zero status when any *error*-level issue remains, which is what causes a CI build to fail.
*Warning*-level issues are reported but do not fail the command unless you pass ``--strict``.

Options
=======

``--dir <path>``, ``-d <path>``
    Path to the technote directory to lint.
    Defaults to the current directory (``.``).
    The command locates :file:`technote.toml`, the content file (:file:`index.rst`, :file:`index.md`, or :file:`index.ipynb`), :file:`requirements.txt`, and :file:`CITATION.cff` within this directory.

``--strict``, ``-s``
    Promote all warnings to errors.
    With this flag, any finding — including the warning-level rules below — causes the command to exit non-zero.

.. _technote-lint-rules:

Rules
=====

Each rule has a stable code so that findings are easy to triage (and, in the future, to except individually), and a landing page describing the rule, showing a failing technote, and walking through the fix.
Codes are grouped by concern: ``TN0xx`` for structural rules, ``TN1xx`` for metadata, and ``TN2xx`` for content.

.. list-table:: Technote lint rules
   :header-rows: 1
   :widths: 12 20 48 20

   * - Code
     - Group
     - Rule
     - Default severity
   * - :doc:`TN001 <tn001>`
     - Structural
     - :file:`technote.toml` conforms to the technote schema.
     - Error
   * - :doc:`TN002 <tn002>`
     - Structural
     - :file:`requirements.txt` declares ``documenteer`` with the ``[technote]`` extra.
     - Warning
   * - :doc:`TN003 <tn003>`
     - Structural
     - :file:`requirements.txt` does not pin Sphinx as a separate requirement.
     - Warning
   * - :doc:`TN004 <tn004>`
     - Structural
     - :file:`technote.toml` exists in the technote directory.
     - Error
   * - :doc:`TN005 <tn005>`
     - Structural
     - :file:`technote.toml` is syntactically valid TOML.
     - Error
   * - :doc:`TN006 <tn006>`
     - Structural
     - The technote has a content file (:file:`index.rst`, :file:`index.md`, or :file:`index.ipynb`).
     - Error
   * - :doc:`TN101 <tn101>`
     - Metadata
     - Every author declares an ``internal_id``.
     - Error
   * - :doc:`TN102 <tn102>`
     - Metadata
     - Each author's ``internal_id`` resolves in the Rubin author database.
     - Error
   * - :doc:`TN103 <tn103>`
     - Metadata
     - The author database is reachable so that IDs can be resolved.
     - Warning
   * - :doc:`TN104 <tn104>`
     - Metadata
     - The declared DOI is syntactically a DOI.
     - Error
   * - :doc:`TN105 <tn105>`
     - Metadata
     - The metadata registered with DataCite for the DOI matches :file:`technote.toml`.
     - Warning
   * - :doc:`TN106 <tn106>`
     - Metadata
     - :file:`CITATION.cff` matches what :file:`technote.toml` generates.
     - Error
   * - :doc:`TN201 <tn201>`
     - Content
     - The content file declares an abstract directive.
     - Error
   * - :doc:`TN202 <tn202>`
     - Content
     - The abstract uses the abstract directive rather than a section heading.
     - Error
   * - :doc:`TN203 <tn203>`
     - Content
     - The content file can be parsed to scan for an abstract.
     - Error
   * - :doc:`TN204 <tn204>`
     - Content
     - The abstract directive has body content.
     - Error

.. toctree::
   :hidden:

   tn001
   tn002
   tn003
   tn004
   tn005
   tn006
   tn101
   tn102
   tn103
   tn104
   tn105
   tn106
   tn201
   tn202
   tn203
   tn204

.. _technote-lint-offline:

Running the linter offline
==========================

Every rule but one reads files alone, so the linter works without a network.
The exception is :doc:`TN105 <tn105>`, which asks DataCite what a technote's DOI is registered as, and :doc:`TN102 <tn102>`/:doc:`TN103 <tn103>`, which resolve author IDs against the Rubin author database.

The two behave differently when the network is not there, and deliberately so:

- An unreachable **author database** is reported as :doc:`TN103 <tn103>`, a warning, because an unresolved ``internal_id`` is the thing that blocks a technote's DOI from being minted — silence would hide it.
- An unreachable **DataCite** is silent. TN105 reports nothing at all, and neither does an unregistered DOI. A technote author working offline gets the same clean run they would get with the network up.

.. _technote-lint-suggested-ids:

Suggested author IDs
====================

An author ``internal_id`` that is missing (:doc:`TN101 <tn101>`) or unknown (:doc:`TN102 <tn102>`) is a dead end on its own, so the linter tries to name the ID you probably want.
It queries the author database twice at most and appends a suggestion when one entry matches confidently:

#. If the author entry declares an ``orcid``, the linter asks the author database which author holds exactly that ORCID.
#. Otherwise — or when nobody holds it — the linter searches the database for the author's name.

.. code-block:: text

   [TN101] Author Yusra AlSayyad is missing an internal_id. Did you mean 'alsayyady' (matched by ORCID)? Run 'documenteer technote sync-authors' to add it.
   [TN102] Author Lynne Jones has internal_id 'lynnej', which is not in the author database. Did you mean 'jonesrl' (R. Lynne Jones, matched by name)?

The message states what the match is based on:

- **matched by ORCID** — the author database holds the author with the ``orcid`` in your :file:`technote.toml` author entry. ORCID is globally unique and author-supplied, so this is the strongest evidence there is: the lookup is exact, and it succeeds however differently your technote and the author database spell the name.
- **matched by name** — a single near-exact name match, whose ORCID (if it has one) does not contradict yours.

Declaring an ``orcid`` for an author is therefore the surest way to get a usable suggestion, and the only one that works when the author database spells the name differently than you do.
It also changes what a TN101 finding asks of you: an ORCID match is one :command:`documenteer technote sync-authors` can act on by itself — it resolves the same ORCID and writes the ``internal_id`` in for you — so the message reads *Run 'documenteer technote sync-authors' to add it*.
A name match is only a suggestion for you to verify and type in, so its message reads *… after adding it*.

The suggestion is deliberately conservative and best-effort: an ambiguous search (several equally good matches, as a common family name gives) or a match contradicted by a differing ORCID adds nothing to the message, and a failed lookup leaves the finding exactly as it would otherwise read.
A suggestion never changes whether the command passes or fails — verify it before you use it.

.. _technote-lint-abstract-scan:

How the abstract is found
=========================

The abstract rules (``TN2xx``) work by scanning the source, not by running a Sphinx build, so it is worth knowing what the scan does and does not see.

- Both the reStructuredText directive (``.. abstract::``) and the MyST fenced directive (a triple-backtick or ``:::`` fence opening with ``{abstract}``) are recognized, in any letter case — docutils lowercases directive names, so a ``{Abstract}`` fence builds and passes.
- In reStructuredText, text on the marker line itself (``.. abstract:: The abstract.``) is directive content and passes.
- Directive *options* (for example ``:class: dropdown``) are configuration rather than content, so a directive holding only options is empty (:doc:`TN204 <tn204>`).
- An abstract factored into another file and pulled in with ``.. include::`` or a MyST ``{include}`` fence is found: those includes are resolved one level deep, relative to the content file. Includes within an included file are not followed, and an include that is missing or points outside the technote directory is ignored (Sphinx reports those itself).
- An :file:`index.ipynb` notebook's markdown cells are concatenated before scanning, so its findings name the file without a line number.

.. _technote-lint-non-sphinx:

Non-Sphinx technotes
====================

Some technote-series repositories are not Sphinx projects at all: they publish through the shared technote CI with a custom build command (an Org-mode deck, for example).
When a directory has no content file (:file:`index.rst`, :file:`index.md`, or :file:`index.ipynb`) *and* no :file:`conf.py`, the linter treats it as one of these and checks only that its :file:`technote.toml` is well formed — :doc:`TN004 <tn004>`, :doc:`TN005 <tn005>`, :doc:`TN001 <tn001>`, and the metadata rules (``TN1xx``), which read :file:`technote.toml` alone.
The :file:`requirements.txt` rules (:doc:`TN002 <tn002>`/:doc:`TN003 <tn003>`), the content rules (``TN2xx``), and :doc:`TN006 <tn006>` are skipped, since they describe a Documenteer/Sphinx build that these repositories do not have.
A repository that *does* have a :file:`conf.py` but no content file is a broken Sphinx technote, and is reported as :doc:`TN006 <tn006>`.

.. note::

   Author ``internal_id`` values are the key to consistent author identification across Rubin documents, and a missing or unknown ID blocks DOI generation.
   See :doc:`../author-metadata` to learn how to add and update the authors that ``TN101``–``TN103`` check.

Related documentation
=====================

- :doc:`../author-metadata` — add and update the authors that :doc:`TN101 <tn101>`–:doc:`TN103 <tn103>` check.
- :doc:`../citation-file` — generate the :file:`CITATION.cff` that :doc:`TN106 <tn106>` keeps in sync with :file:`technote.toml`.
- :doc:`../migrate` — the migration tool sets up the :file:`Makefile`, :file:`requirements.txt`, and abstract directive that these rules rely on.
