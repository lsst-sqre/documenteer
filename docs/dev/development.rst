#################
Development guide
#################

This page provides procedures and guidelines for developing and contributing to Documenteer.

Scope of contributions
======================

Documenteer is an open source package, meaning that you can contribute to Documenteer itself, or fork Documenteer for your own purposes.

Since Documenteer is intended for internal use by LSST, community contributions can only be accepted if they align with LSST's aims.
For that reason, it's a good idea to propose changes with a new `GitHub issue`_ before investing time in making a pull request.

Documenteer is developed by the LSST SQuaRE team.
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
   pip install -e ".[dev,pipelines,technote]"

The ``dev`` extra includes test and documentation dependencies.
You also need to install the ``pipelines`` and ``technote`` extras to ensure that all tests will run.

.. _dev-run-tests:

Running tests
=============

Run pytest_ from the root of the source repository:

.. code-block:: sh

   pytest

Pytest also runs code style linting (through pytest-flake8), coverage analysis (through pytest-coverage), and static type checking (through pytest-mypy).

The pytest command *must* succeed for a pull request to be accepted.

.. _pytest: https://pytest.org

.. _dev-build-docs:

Building documentation
======================

Documentation is built with Sphinx_:

.. _Sphinx: https://www.sphinx-doc.org/en/master/

.. code-block:: sh

   cd docs
   make html

To clear the built output:

.. code-block:: sh

   make clean

To check links:

.. code-block:: sh

   make linkcheck

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

- Follow :pep:`8` for code style.
  Flake8 should detect any issues for you.

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

.. _`LSST DM User Documentation Style Guide`: https://developer.lsst.io/user-docs/index.html
.. _`Google Developer Style Guide`: https://developers.google.com/style/
.. _`LSST DM Docstring Style Guide`: https://developer.lsst.io/python/style.html
.. _`LSST DM ReStructuredTextStyle Guide`: https://developer.lsst.io/restructuredtext/style.html
