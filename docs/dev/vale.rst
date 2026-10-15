###########################
Editorial linting with Vale
###########################

Documenteer's documentation uses Vale_ to lint its prose against the `LSST DM User Documentation Style Guide`_ and the `Google Developer Documentation Style Guide`_ that it builds on.
Vale's feedback is *advisory*: it never fails a build, is not part of the default nox sessions or the prek hooks, and is not a required check on pull requests.
Use it as a checklist of things to look at while writing or revising a page, not as a gate.

.. _Vale: https://vale.sh
.. _`Google Developer Documentation Style Guide`: https://developers.google.com/style/

What Vale checks
================

Vale runs three sets of rules over the ``.rst`` and ``.md`` files under ``docs/``:

- ``Vale.Spelling`` — spell-checking, using the project vocabulary (see below) for legitimate project and software terms.
- **Google** — the Google Developer Documentation Style Guide package, tuned for this corpus.
  Some of its rules are demoted to suggestions or turned off where they produce noise on reference documentation.
  See the comments in ``.vale.ini`` for the rationale behind each adjustment.

.. vale off

- **Documenteer** — a small set of house rules, such as addressing the reader as "you" rather than "we" and not using "here" as link text.

.. vale on

The configuration lives in ``.vale.ini`` at the repository root, and the Documenteer rules live in ``styles/Documenteer/``.

Some paths are excluded because their prose is generated or has no prose: the change log (``docs/changelog.md``, a symlink to the scriv-generated ``CHANGELOG.md``), the shared link targets in ``docs/_rst_epilog.rst``, the generated API stubs under ``docs/dev/api/contents/``, and the technote templates under ``docs/technotes/_templates/``.

Running Vale locally
====================

Run Vale over the whole documentation set with nox:

.. code-block:: sh

   uv run --only-group=nox nox -s vale

This installs Vale and docutils from the ``vale`` dependency group, runs ``vale sync`` to download the Google package into ``styles/`` (which is gitignored), and lints ``docs/``.
A non-zero exit code from Vale just means it found something to report; the session treats it as a success.

To get feedback on the page you are working on, pass its path (or several paths) after ``--``:

.. code-block:: sh

   uv run --only-group=nox nox -s vale -- docs/guides/citations/index.rst

What happens in CI
==================

On a pull request, GitHub Actions runs Vale too, and posts any findings on the lines you changed as inline annotations.
That job is always green, even when Vale has findings, and it is not required for merging or releasing.

The weekly periodic workflow additionally runs Vale over the whole corpus and uploads the report as a ``vale-report`` artifact, as a snapshot of where the documentation stands.

Adding words to the vocabulary
==============================

When Vale flags a legitimate project term, a piece of software, or an identifier as a misspelling, add it to the project vocabulary rather than working around it.
The vocabulary is a plain-text file at ``styles/config/vocabularies/Documenteer/accept.txt``.
Each line is a case-sensitive regular expression.
Add the term on its own line, grouped under the appropriate comment heading.

Before you accept a word, make sure it's genuinely a term and not a typo.
If a flagged word is actually a typo, fix it in the source instead of accepting it.

Suppressing false positives
===========================

Occasionally a rule fires on something that's correct in context.
When that happens, you can turn Vale off for a span of source with comments:

.. code-block:: rst

   .. vale off

   This text is not linted by Vale.

   .. vale on

Use this sparingly, and only for genuine false positives — for example, a required verbatim string that happens to trip a rule.
Prefer adding a real term to the vocabulary over switching Vale off, and never use ``.. vale off`` to silence a legitimate style issue that you should fix instead.

One known limitation worth a suppression: Vale parses reStructuredText through docutils, which does not know Sphinx-only ``code-block`` options such as ``:emphasize-lines:``.
A code block that uses them leaks its contents into the prose, so its identifiers show up as spelling errors.
Either drop the option or wrap the block in ``.. vale off`` / ``.. vale on``.
