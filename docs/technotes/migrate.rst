:og:description: Rubin Observatory has a new technical note format for Markdown and reStructuredText documents. This page provides a guide to migrating legacy reStructuredText/Sphinx technotes to the current format.

######################################################
Migrate legacy reStructuredText/Sphinx technical notes
######################################################

Introduced in December 2023, Rubin Observatory has a new technical note format for Markdown and reStructuredText documents.
This update provides many `new features <https://community.lsst.org/t/the-next-generation-of-rubin-observatory-technotes-with-documenteer-1-0/8166>`__ included a responsive and branded page design, Markdown support, improved build configuration, automated bibliography management, and citation-ready metadata.

This page shows how to migrate your existing technotes with a command-line tool that largely automates the process.
This page also provides file-by-file notes in case you need to revise the migration.

.. tip::

   Your technote is in the legacy format if it has a :file:`metadata.yaml` file at the top level of its repository.

   LaTeX-format technotes are unaffected by this migration.

Step 1. Install pipx
====================

The migration tool needs **Python 3.11 or later**.
You can verify this by running ``python --version`` from your shell.

This official migration procedure uses the pipx_ tool to install and run the migration tool in an isolated Python environment.
You can verify that pipx_ is installed by running ``pipx --version`` from your shell and checking for a version number.

If you don't have the :command:`pipx` command-line tool already, you can install ``pipx`` several ways:

.. tab-set::

   .. tab-item:: pip

      .. prompt:: bash

         python -m pip install pipx

   .. tab-item:: conda-forge

      .. prompt:: bash

         conda install -c conda-forge pipx

   .. tab-item:: homebrew

      .. prompt:: bash

         brew install pipx

Step 2. Clone your technote and create a branch
===============================================

Since the migration is performed locally, you need to clone the repository:

.. code-block:: bash

   git clone https://github.com/{org}/{repo}

Then create a branch for the migration (see the `Developer Guide <https://developer.lsst.io/work/flow.html>`_ for more information on branching):

.. code-block:: bash

   git switch -c {...}

Working from a branch allows you to create a pull request to verify the migration before merging it into the main branch.

Step 3. Look up author IDs
==========================

The migration tool needs the IDs of the technote's authors to fully configure the technote's metadata.

Open `authordb.yaml`_ on GitHub and find the YAML keys that identify the technote's authors.
For example, ``sickj`` is the ID for Jonathan Sick.

.. _technote-migration-tool:

Step 4. Run the migration tool
==============================

From the root of the cloned technote repository, run the migration tool, listing any identified authors that are relevant to your technote:

.. code-block:: bash
   :caption: Set author IDs with the -a option

   pipx run documenteer technote migrate -a sickj -a economouf

When the migration runs, it shows a summary of the files changed and deleted.
Use ``git diff`` to review the changes in case you need to make tweaks before committing.

If you want to learn more about the changes made by the migration tool, you can review the :ref:`detailed changes, below <technote-migration-detailed>`.

.. _technote-migration-markdown:

Step 5 (optional). Migrate to Markdown
======================================

The new technote format supports Markdown as well as reStructuredText.
If you wish to use Markdown, you can use MyST Parser's migration tool:

.. prompt:: bash

   pipx install "rst-to-myst[sphinx]"
   rst2myst convert index.rst

The Markdown flavor used by the new technote format is MyST Markdown, which is a superset of CommonMark Markdown with support for Sphinx roles and directives.
See the `MyST Parser documentation <https://myst-parser.readthedocs.io/en/latest/syntax/roles-and-directives.html#roles-directives>`__ for more information.

Step 6 (optional). Build the technote locally
=============================================

You can build the technote locally to verify that the migrated technote compiles successfully.

GitHub Actions will test the technote build when you open a pull request (next step), so you can skip this step.
However, you can get faster feedback by building locally.

.. prompt:: bash

   make init
   make html

The technote's website will be in the ``_build/html`` directory.
Open the ``index.html`` file in your web browser to view the technote:

.. prompt:: bash

   open _build/html/index.html

You can repeat the :command:`make html` command to rebuild the technote after making changes.

You might also want to run the linter to check links and find common issues:

.. prompt:: bash

   make lint

If you have any questions or issues about the build, you should still proceed with committing and creating a pull request (see next step).
This way you can link to the repository when you reach out for help in `#square-docs-support`_ on Slack.

Step 7. Commit the migration, pull request, and merge
=====================================================

At this point, you should have a working technote in the new format.
If you haven't already, commit your work, push your branch to the GitHub repository, and open a pull request.
GitHub Actions will build the technote and publish a preview version that is linked from the ``/v`` path of your technote's website.

If the build works, you can merge the pull request.

If there are build errors, you can reach out to `#square-docs-support`_ on Slack for help.
Include the repository URL and ideally a link to the pull request or GitHub Actions workflow run that failed.

.. _technote-migration-detailed:

Migration details
=================

The migration is automated by the :command:`documenteer technote migrate` command, as described above.
This section describes the steps performed by the migration tool in detail in case you need to make adjustments or understand the changes made to your technote.

technote.toml file (added)
--------------------------

The :file:`technote.toml` file replaces the original :file:`metadata.yaml` file.
This new file provides both metadata and Sphinx configuration for your document.

Here is a simple :file:`technote.toml` file:

.. code-block:: toml
   :caption: technote.toml

   [technote]
   id = "EXAMPLE-000"
   series_id = "EXAMPLE"
   canonical_url = "https://example-000.lsst.io/"
   github_url = "https://github.com/lsst/example-000"
   github_default_branch = "main"
   date_created = 2015-11-18
   date_updated = 2023-11-01
   organization.name = "Vera C. Rubin Observatory"
   organization.ror = "https://ror.org/048g3cy84"
   license.id = "CC-BY-4.0"

   [[technote.authors]]
   name = {given = "Drew", family = "Developer"}
   internal_id = "example"
   orcid = "https://orcid.org/0000-0001-2345-6789"
   [[technote.authors.affiliations]]
   name = "Rubin Observatory Project Office"
   internal_id = "RubinObs"

.. note::

   The schema for this file is described in the `Technote package documentation <https://technote.lsst.io/user-guide/technote-toml.html>`__, and elsewhere in the :doc:`Documenteer documentation for Rubin technotes <index>`.
   For now, some pointers on important metadata:

   - ``id`` is the technote's handle. A lower-cased version of the handle is the subdomain of the technote's website.
     For example, the handle for https://sqr-000.lsst.io/ is ``SQR-000``.
   - ``series_id`` is the technote's series handle. At Rubin, this is the handle's prefix. Common series include ``RTN``, ``DMTN``, ``SQR``, and ``SITCOMTN``.
   - ``canonical_url`` is the URL of the technote's website.
   - ``github_url`` is the URL of the technote's GitHub repository.
   - ``date_created`` is an optional field that specifies when the technote was first created.
   - ``date_updated`` is an optional field that specifies when the technote was last updated. If you omit this field, the current date is used.
   - Each author is specified with a ``[[technote.authors]]`` table (in TOML, the double brackets represent a table in an **array of tables**). Use the :command:`make add-author` command to add an author to this file using data from `authordb.yaml`_. It's important to use the ``internal_id`` field to identify authors with their corresponding key in `authordb.yaml`_. This enables Documenteer to update author information with the :command:`make sync-authors` command.

conf.py file (updated)
----------------------

The :file:`conf.py` file directly configures the Sphinx build process.
New technotes use a different configuration set provided by Documenteer that uses :file:`technote.toml` to customize the Sphinx configuration.
For most technotes, the :file:`conf.py` file should be a single line:

.. code-block:: python
   :caption: conf.py

   from documenteer.conf.technote import *  # noqa: F401, F403

If your :file:`conf.py` file has additional content, some of that configuration may be migrated to :file:`technote.toml`.
Reach out to `#square-docs-support`_ on Slack for advice.

index.rst file (updated)
------------------------

The :file:`index.rst` file is the main content file for your technical note.
The new technote format requires some changes to this file: the title is now part of the content, the abstract is marked up with a directive, status information is now part of :file:`technote.toml`, and the configuration for the reference section is dramatically simplified.

Additionally, the new technote format supports Markdown as well as reStructuredText.
See :ref:`migrate to Markdown <technote-migration-markdown>` to learn how to switch to Markdown.

.. tip::

   Besides these changes, your technote can also be written in Markdown (:file:`index.md`).
   If you wish to switch from ReStructuredText to Markdown, you can use MyST Parser's migration tool:

   .. prompt:: bash

      pipx install "rst-to-myst[sphinx]"
      rst2myst convert index.rst

   This procedure uses pipx_ to install the ``rst-to-myst`` tool in an isolated Python environment (you might have already installed pipx_ to run the :ref:`main migration tool <technote-migration-tool>`).

   Finally, delete the original :file:`index.rst` file and edit :file:`index.md` to fix any formatting issues.

   .. prompt:: bash

      git rm index.rst
      git add index.md
      git commit -m "Switch to Markdown format"

Title
~~~~~

The title is now part of the content, not the metadata.
Add the title to the top of the content:

.. tab-set::

   .. tab-item:: rst

      .. code-block:: rst
         :caption: index.rst

         ######################
         Example technical note
         ######################

         [... content below ...]

   .. tab-item:: md

      .. code-block:: md
         :caption: index.md

         # Example technical note

Document status
~~~~~~~~~~~~~~~

The original technote format used a ``note`` directive to describe whether the document was a draft or deprecated.
Now this status metadata is structured in :file:`technote.toml`.
Delete the ``note`` directive and add the status information to :file:`technote.toml` following :doc:`document-status`.

Abstract
~~~~~~~~

Legacy technotes either provided an abstract or summary through the ``description`` field in :file:`metadata.yaml`, in a ``note`` directive in :file:`index.rst`, or in a content section in :file:`index.rst`.
The new technote format uses an ``abstract`` directive to mark up the abstract/summary.

.. tab-set::

   .. tab-item:: rst

      .. code-block:: rst
         :caption: index.rst
         :emphasize-lines: 5,6,7

         ######################
         Example technical note
         ######################

         .. abstract::

            This is a summary of the technical note.

         Introduction
         ============

         [... content below ...]

   .. tab-item:: md

      .. code-block:: md
         :caption: index.md
         :emphasize-lines: 3,4,5

         # Example technical note

         ```{abstract}
         This is a summary of the technical note.
         ```

         ## Introduction

         [... content below ...]

Reference section
~~~~~~~~~~~~~~~~~

If your technote makes references to other documents with roles like :external+sphinxcontrib-bibtex:rst:role:`cite`, you'll need a reference section to display the bibliography.
In the new technote format, this section is simplified:

.. tab-set::

   .. tab-item:: rst

      .. code-block:: rst
         :caption: index.rst

         [... content above ...]

         References
         ==========

         .. bibliography::

   .. tab-item:: md

      .. code-block:: md
         :caption: index.md

         [... content above ...]

         ## References

         ```{bibliography}
         ```

Specifically:

- The references section should be a regular section, not a "rubric."
- The bibliography directive no longer requires any configuration; all configuration is provided by Documenteer.

metadata.yaml file (deleted)
----------------------------

At this point, all relevant metadata about the technote is in :file:`technote.toml` or :file:`index.rst`/:file:`index.md`.
Delete the deprecated :file:`metadata.yaml` file:

.. prompt:: bash

   git rm metadata.yaml

lsstbib/ directory (deleted)
----------------------------

The legacy technote format vendored Rubin BibTeX bibliography files from https://github.com/lsst/lsst-texmf.
The new technote format automatically downloads and caches these files so that you no longer need to commit them into your repository.
Delete the :file:`lsstbib` directory:

.. prompt:: bash

   git rm -r lsstbib

.gitignore file (updated)
-------------------------

The new technote format introduces additional directories that should be ignored by Git.
Ensure at least the following paths are included in the :file:`.gitignore` file:

.. literalinclude:: ../../src/documenteer/storage/localtemplates/technote/gitignore
   :language: text
   :caption: .gitignore

.pre-commit-config.yaml file (added)
------------------------------------

Pre-commit_ is a Python package that runs validation and formatting checks on your technote's repository before you commit.
Although it is not required, it's highly recommended that you set up pre-commit hooks for your technote.
To start, add a :file:`.pre-commit-config.yaml` file:

.. literalinclude:: ../../src/documenteer/storage/localtemplates/technote/pre-commit-config.yaml
   :language: yaml
   :caption: .pre-commit-config.yaml

.. tip::

   You can add additional pre-commit hooks to this file to suite your needs.
   See Pre-commit's `directory of available hooks <https://pre-commit.com/hooks.html>`__ for ideas.

requirements.txt file (updated)
-------------------------------

The Python dependencies for your technote are listed in a :file:`requirements.txt` file that should now look like this:

.. literalinclude:: ../../src/documenteer/storage/localtemplates/technote/requirements.txt
   :language: text
   :caption: requirements.txt

.. note::

   If your technote has additional dependencies listed, you can reach out to `#square-docs-support`_ on Slack if you are unsure whether they are part of the Sphinx build process or separate packages needed for any custom document preprocessing.

tox.ini file (added)
--------------------

Tox_ is a tool for running Python programs in dedicated virtual environments.
This makes your local technote builds more reproducible by separating the technote's dependencies from your system and other projects.

This is the recommended tox configuration to start with:

.. literalinclude:: ../../src/documenteer/storage/localtemplates/technote/tox.ini
   :language: ini
   :caption: tox.ini

Makefile file (updated)
-----------------------

The :file:`Makefile` file provides a simple entrypoint for building your technote and performing other common tasks.
This is the suggested content for your :file:`Makefile` that works with the tox and pre-commit configurations:

.. literalinclude:: ../../src/documenteer/storage/localtemplates/technote/Makefile
   :language: make
   :caption: Makefile

.github/workflows/ci.yaml file (added/updated)
----------------------------------------------

Recent technotes have already migrated their GitHub Actions workflows to use the reusable workflow from https://github.com/lsst-sqre/rubin-sphinx-technote-workflows.
Check the :file:`.github/workflows/ci.yaml` file to make sure it looks like this:

.. code-block:: yaml
   :caption: .github/workflows/ci.yaml

   name: CI

   'on': [push, pull_request, workflow_dispatch]

   jobs:
     call-workflow:
       uses: lsst-sqre/rubin-sphinx-technote-workflows/.github/workflows/ci.yaml@v1
       with:
         handle: example-001
       secrets:
         ltd_username: ${{ secrets.LTD_USERNAME }}
         ltd_password: ${{ secrets.LTD_PASSWORD }}

Replace ``example-001`` with your technote's handle (the subdomain of ``lsst.io``).

.. note::

   The original Rubin technotes used Travis CI for continuous integration and deployment, but we no longer use that service.
   In that case, you will need to create the :file:`.github/workflows` directory and add the above :file:`ci.yaml` workflow.
   GitHub Actions will automatically start using this workflow.

   If your technote has a :file:`.travis.yml` file, you should delete it:

   .. prompt:: bash

      git rm .travis.yml

.github/dependabot.yml file (added)
-----------------------------------

Dependabot is a service provided by GitHub that generates pull requests when there are new versions of your technote's dependencies.
Set up Dependabot by adding a :file:`.github/dependabot.yml` file:

.. literalinclude:: ../../src/documenteer/storage/localtemplates/technote/dependabot.yml
   :language: yaml
   :caption: .github/dependabot.yml

README.rst or README.md file (updated)
--------------------------------------

The README for a legacy-format technote likely has outdated information about how to build the technote.
Here is a suggested README template for technotes in the new format:

.. tab-set::

   .. tab-item:: rst

      .. literalinclude:: _templates/README.rst
         :language: rst
         :caption: README.rst

   .. tab-item:: md

      .. literalinclude:: _templates/README.md
         :language: md
         :caption: README.md
