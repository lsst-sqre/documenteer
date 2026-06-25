#################
Development guide
#################

This page provides procedures and guidelines for developing and contributing to Documenteer.

Scope of contributions
======================

Documenteer is an open source package, meaning that you can contribute to Documenteer itself, or fork Documenteer for your own purposes.

Since Documenteer is intended for internal use by Rubin Observatory, community contributions can only be accepted if they align with the Rubin Observatory's aims.
For that reason, it's a good idea to propose changes with a new `GitHub issue`_ before investing time in making a pull request.

Documenteer is developed by the SQuaRE team.
The lead developer and maintainer is `Jonathan Sick`_.

.. _GitHub issue: https://github.com/lsst-sqre/documenteer/issues/new
.. _Jonathan Sick: https://github.com/jonathansick

.. _dev-environment:

Environment set up
==================

To develop Documenteer, create a virtual environment with your method of choice (like virtualenvwrapper) and then clone or fork, and install:

.. code-block:: sh

   git clone https://github.com/lsst-sqre/documenteer.git
   cd documenteer
   make init

A complete environment also needs the compiled web assets (see :doc:`theme-assets`).
Because the asset build pulls the private ``@lsst-sqre/rubin-style-dictionary`` package from GitHub Packages, you must first :ref:`authenticate npm to GitHub Packages <theme-assets-github-packages>` with a classic ``read:packages`` personal access token.

.. _dev-prek:

Code formatting and linting with prek
=====================================

Documenteer uses `prek`_ (a drop-in, config-compatible replacement for pre-commit) to automatically and consistently format and lint the codebase on each commit.
By running ``make init``, prek is already installed in your environment.

If prek "fails" because the black_ or isort_ code formatters changed the source, simply ``git add`` the changes and try the commit again.

To learn more about the hook configuration, see the ``.pre-commit-config.yaml`` file in the repository (prek reads the same configuration format as pre-commit).

.. _dev-nox:

Running tests via nox
=====================

Development tasks are run through nox_ (via `nox-uv`_), which is provisioned by the ``make init`` command.
Run nox through uv so the runner and its environments are managed for you:

.. code-block:: sh

   uv run --only-group=nox nox

Running ``nox`` with no arguments runs the default sessions (lint, typing, the Sphinx 8 and 9 test runs, and a docs build).
The available sessions are:

.. list-table:: nox sessions
   :widths: 40 60
   :header-rows: 1

   * - Session
     - Description
   * - ``test``
     - Run the test suite with pytest. Parametrized over Sphinx versions (``8``, ``9``, ``dev``). Coverage is opt-in (see below).
   * - ``typing``
     - Run mypy (type annotations checker). Parametrized over Sphinx versions (``8``, ``9``, ``dev``).
   * - ``lint``
     - Run the prek hooks (including the prettier web-asset hook).
   * - ``coverage-report``
     - Aggregate unit test coverage reports from the ``test`` sessions and display a report. Runs automatically after the ``test`` sessions when ``DOCUMENTEER_COVERAGE`` is set.
   * - ``docs`` / ``docs-linkcheck``
     - Build the documentation and check its links.
   * - ``demo``
     - Build the demo technote projects as an end-to-end test.
   * - ``packaging``
     - Build the PyPI package and check it with twine.

By default the ``test`` session runs without coverage instrumentation.
To collect coverage and print a combined report across the test sessions, set ``DOCUMENTEER_COVERAGE``, e.g. ``DOCUMENTEER_COVERAGE=1 uv run --only-group=nox nox``.

It is also possible to run individual sessions, for example:

.. code-block:: sh

   uv run --only-group=nox nox -s lint

The ``test`` and ``typing`` sessions are parametrized over Sphinx versions.
Select a specific version with the parametrized session name, for example to type-check against Sphinx 8:

.. code-block:: sh

   uv run --only-group=nox nox -s "typing(sphinx='8')"

To learn more about the available sessions, run ``nox -l`` or review the :file:`noxfile.py` file in the code repository.

.. _nox: https://nox.thea.codes/
.. _nox-uv: https://github.com/dantebben/nox-uv

.. _dev-run-tests:

Running tests through pytest
============================

Although nox is the recommended method for running tests, it is still possible to run tests directly through pytest_:

.. code-block:: sh

   pytest

This is particularly useful for running a single test module (provide the test module's path as an argument to the ``pytest`` command).

.. _dev-build-docs:

Building documentation
======================

Documentation is built with Sphinx_:

.. _Sphinx: https://www.sphinx-doc.org/en/master/

.. code-block:: sh

   uv run --only-group=nox nox -s docs

The HTML output is located in the :file:`docs/_build/html` directory.

To check links:

.. code-block:: sh

   uv run --only-group=nox nox -s docs-linkcheck

.. _dev-change-log:

Updating the change log
=======================

Each pull request should update the change log (:file:`CHANGELOG.rst`).
Add a description of new features and fixes as list items under a section at the top of the change log called "Unreleased:"

.. code-block:: rst

   Unreleased
   ----------

   - Description of the feature or fix.

If the next version is known (because Documenteer's master branch is being prepared for a new major or minor version), the section may contain that version information:

.. code-block:: rst

   X.Y.0 (unreleased)
   ------------------

   - Description of the feature or fix.

If the exact version and release date is known (:doc:`because a release is being prepared <release>`), the section header is formatted as:

.. code-block:: rst

   X.Y.0 (YYYY-MM-DD)
   ------------------

   - Description of the feature or fix.

.. _style-guide:

Style guide
===========

Code
----

- Code formatting is performed automatically through `black`_ and `isort`_.
  Generally this means that the code base automatically conforms to :pep:`8` and will pass the flake8 linter.

- Write tests for Pytest_.

- Use :pep:`484` type annotations wherever possible, especially for new code.

- Use Click for command-line interfaces.

Documentation
-------------

- Follow the `LSST DM User Documentation Style Guide`_, which is primarily based on the `Google Developer Style Guide`_.

- Document the Python API with numpydoc-formatted docstrings.
  See the `LSST DM Docstring Style Guide`_.

- Follow the `LSST DM ReStructuredTextStyle Guide`_.
  In particular, ensure that prose is written **one-sentence-per-line** for better Git diffs.
