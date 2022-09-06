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

.. _dev-pre-commit:

Code formatting and linting with pre-commit
===========================================

Documenteer uses `pre-commit`_ to automatically and consistently format and lint the codebase on each commit.
By running ``make init``, pre-commit is already installed in your environment.

If pre-commit "fails" because the black_ or isort_ code formatters changed the source, simply ``git add`` the changes and try the commit again.

To learn more about the pre-commit configuration, see the ``.pre-commit-config.yaml`` file in the repository.

.. _dev-tox:

Running tests via tox
=====================

The best way to run tests is through tox, which is pre-installed through the ``make init`` command:

.. code-block:: sh

   tox

There are multiple test environments, the default environments include:

.. list-table:: Default tox environments
   :widths: 40 60
   :header-rows: 1

   * - Enviroment
     - Description
   * - ``py37-test-sphinxlatest``
     - Run tests in Python 3.7 with latest release of Sphinx
   * - ``py38-test-sphinxlatest``
     - Run tests in Python 3.8 with latest release of Sphinx
   * - ``typing-sphinxlatest``
     - Run mypy (type annotations checker) against latest release of Sphinx
   * - ``lint``
     - Run linters, such as flake8 and Sphinx linkcheck.
   * - ``coverage-report``
     - Aggregates unit test coverage reports from individual "test" runs and displays a report.

It is also possible to run individual tox environments, for example:

.. code-block:: sh

   tox -e typing-sphinxlatest

Additional tox environments are available for testing against different versions of Sphinx.
For example, to test against Sphinx 2.3.x, run:

.. code-block:: sh

   tox -e py37-test-sphinx23

To learn more about the available tox environments, review the :file:`tox.ini` file in the code repository.

.. _dev-run-tests:

Running tests through pytest
============================

Although tox is the recommended method for running tests, it is still possible to run tests directly through pytest_:

.. code-block:: sh

   pytest

This is particularly useful for running a single test module (provide the test module's path as an argument to the ``pytest`` command).

.. _dev-build-docs:

Building documentation
======================

Documentation is built with Sphinx_:

.. _Sphinx: https://www.sphinx-doc.org/en/master/

.. code-block:: sh

   tox -e docs

The HTML output is located in the :file:`docs/_build/html` directory.

To check links:

.. code-block:: sh

   tox -e docs-lint

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
