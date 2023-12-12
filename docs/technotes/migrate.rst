#####################################
Migrate legacy Sphinx technical notes
#####################################

Introduced in December 2023, Rubin Observatory has a new technical note format for Markdown and reStructuredText documents, based on the Sphinx_ and `Technote <https://technote.lsst.io>`__ Python packages.
If you started writing your technical note before December 2023, it is likely in the legacy Sphinx format.
You can tell if your technical note is in the legacy format if it has a :file:`metadata.yaml` file.
If you are continuing to write such a technical note, you should migrate it to the new format to take advantage of new features.
This page provides a guide to migrating your technical note to the new format.

To get started on your migration, be sure to have your technote repository checked-out locally.
Work on a ticket branch, `per the Developer Guide <https://developer.lsst.io/work/flow.html>`__, so you can check your work with a pull request before merging to the ``main`` branch.

Running the migration tool
==========================

Documenteer provides a migration tool, :command:`documenteer technote migrate`, that can help automate this process.

If you cannot use this tool, you can follow the `detailed steps <#technote-migration-detailed>`__ below.
For example, if you have a customized build process, you may want to manually migrate your technote.
Alternatively you can run the migration tool, and then use Git to unstage any changes you don't want to commit.

Preparation
-----------

To run the migration command in an isolated Python environment, without affecting other projects, you can use the ``pipx`` tool.
First, install ``pipx``:

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

.. important::

   Documenteer, and therefore pipx, need Python 3.11 or later.

Run the migration
-----------------

From the root of the cloned technote repository, you can run the migration tool:

.. prompt:: bash

   pipx run documenteer technote migrate

.. tip::

   You can also add author information during the migration.
   Open `authordb.yaml`_ on GitHub and find the keys that identify the technote's authors.
   For example, ``sickj`` is the key for Jonathan Sick.
   Then run the migration command with a ``-a`` option for each author:

   .. prompt:: bash

      pipx run documenteer technote migrate -a sickj -a economouf

When the migration runs, it shows a summary of the files changed and deleted.
Use ``git diff`` to see the changes in detail.
You may want to tweak those changes before committing them.

If you want to learn more about the changes made by the migration tool, you can review the :ref:`detailed steps below <technote-migration-detailed>`.

.. _technote-migration-detailed:

Detailed steps
==============

Step 1. Create a technote.toml file
-----------------------------------

The :file:`technote.toml` file replaces the original :file:`metadata.yaml` file.
This new file provides both metadata and Sphinx configuration for your document.

Here is a simple :file:`technote.toml` file to get you started:

.. code-block:: toml

   [technote]
   id = "EXAMPLE-000"
   series_id = "EXAMPLE"
   canonical_url = "https://example-000.lsst.io/"
   github_url = "https://github.com/lsst/example-000"
   github_default_branch = "main"
   date_created = 2015-11-18
   date_updated = 2023-11-01

   [[technote.authors]]
   name = {given = "Drew", family = "Developer"}
   internal_id = "example"
   orcid = "https://orcid.org/0000-0001-2345-6789"
   [[technote.authors.affiliations]]
   name = "Rubin Observatory Project Office"
   internal_id = "RubinObs"

When you're done, add this file to your repository and commit it:

.. prompt:: bash

   git add technote.toml
   git commit -m "Add technote.toml file"

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
   - Each author is specified with a ``[[technote.authors]]`` table (in TOML, the double brackets represent a table in an **array of tables**). Use the :command:`mamke add-author` command to add an author to this file using data from `authordb.yaml`_. It's important to use the ``internal_id`` field to identify authors with their corresponding key in `authordb.yaml`_. This enables Documenteer to update author information with the :command:`make sync-authors` command.

Step 2. Update conf.py
----------------------

The :file:`conf.py` file directly configures the Sphinx build process.
New technotes use a different configuration set provided by Documenteer that uses :file:`technote.toml` to customize the Sphinx configuration.
For most technotes, the :file:`conf.py` file should be a single line:

.. code-block:: python

   from documenteer.conf.technote import *  # noqa: F401, F403

Commit any changes:

.. prompt:: bash

   git add conf.py
   git commit -m "Update conf.py to new technote format"

If your :file:`conf.py` file has additional content, some of that configuration may be migrated to :file:`technote.toml`.
Reach out to `#dm-docs-support`_ on Slack for advice.

Step 3. Update the index.rst file
---------------------------------

The :file:`index.rst` file is the main content file for your technical note.
The new technote format requires some changes to this file: the title is now part of the content, the abstract is marked up with a directive, status information is now part of :file:`technote.toml`, and the configuration for the reference section is dramatically simplified.

.. tip::

   Besides these changes, your technote can also be written in Markdown (:file:`index.md`).
   If you wish to switch from ReStructuredText to markdown, install pandoc and run:

   .. prompt:: bash

      pandoc -f rst -t markdown -o index.md index.rst

   Then, delete the original :file:`index.rst` file and edit :file:`index.md` to fix any formatting issues.

   .. prompt:: bash

      git rm index.rst
      git add index.md
      git commit -m "Switch to Markdown format"

Add the title
~~~~~~~~~~~~~

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

Move document status information to technote.toml
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The original technote format used a ``note`` directive to describe whether the document was a draft or deprecated.
Now this status metadata is structured in :file:`technote.toml`.
Delete the ``note`` directive and add the status information to :file:`technote.toml` following :doc:`document-status`.

Format the abstract/summary with the abstract directive
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

Simplify the reference section
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

Commit any changes
~~~~~~~~~~~~~~~~~~

.. tab-set::

   .. tab-item:: rst

      .. prompt:: bash

         git add index.rst
         git commit -m "Reformat index.rst for new technote format"

   .. tab-item:: md

      .. prompt:: bash

         git add index.md
         git commit -m "Reformat index.md for new technote format"

Step 4. Delete metadata.yaml
----------------------------

At this point, all relevant metadata about the technote is in :file:`technote.toml` or :file:`index.rst`/:file:`index.md`.
Delete the deprecated :file:`metadata.yaml` file:

.. prompt:: bash

   git rm metadata.yaml
   git commit -m "Remove metadata.yaml file"

Step 5. Delete the lsstbib/ directory
-------------------------------------

The legacy technote format vendored Rubin BibTeX bibliography files from https://github.com/lsst/lsst-texmf.
The new technote format automatically downloads and caches these files so that you no longer need to commit them into your repository.
Delete the :file:`lsstbib` directory:

.. prompt:: bash

   git rm -r lsstbib
   git commit -m "Remove lsstbib/ directory"

Step 6. Update .gitignore
-------------------------

The new technote format introduces additional directories that should be ignored by Git.
Ensure at least the following paths are included in the :file:`.gitignore` file:

.. literalinclude:: ../../src/documenteer/storage/localtemplates/technote/gitignore
   :language: text
   :caption: .gitignore

.. prompt:: bash

   git add .gitignore
   git commit -m "Update .gitignore file"

Step 7. Set up pre-commit hooks
-------------------------------

Pre-commit_ is a Python package that runs validation and formatting checks on your technote's repository before you commit.
Although it is not required, it's highly recommended that you set up pre-commit hooks for your technote.
To start, add a :file:`.pre-commit-config.yaml` file:

.. literalinclude:: ../../src/documenteer/storage/localtemplates/technote/pre-commit-config.yaml
   :language: yaml
   :caption: .pre-commit-config.yaml

Commit any changes:

.. prompt:: bash

   git add .pre-commit-config.yaml
   git commit -m "Add pre-commit configuration"

.. tip::

   You can add additional pre-commit hooks to this file to suite your needs.
   See Pre-commit's `directory of available hooks <https://pre-commit.com/hooks.html>`__ for ideas.

Step 8. Update requirements.txt
-------------------------------

The Python dependencies for your technote are listed in a :file:`requirements.txt` file that should now look like this:

.. literalinclude:: ../../src/documenteer/storage/localtemplates/technote/requirements.txt
   :language: text
   :caption: requirements.txt

Commit any changes:

.. prompt:: bash

   git add requirements.txt
   git commit -m "Update requirements.txt file"

.. note::

   If your technote has additional dependencies listed, you can reach out to `#dm-docs-support`_ on Slack if you are unsure whether they are part of the Sphinx build process or separate packages needed for any custom document preprocessing.

Step 9. Add a tox.ini file
--------------------------

Tox_ is a tool for running Python programs in dedicated virtual environments.
This makes your local technote builds more reproducible by separating the technote's dependencies from your system and other projects.

This is the recommended tox configuration to start with:

.. literalinclude:: ../../src/documenteer/storage/localtemplates/technote/tox.ini
   :language: ini
   :caption: tox.ini

Step 10. Update the Makefile
----------------------------

The :file:`Makefile` file provides a simple entrypoint for building your technote and performing other common tasks.
This is the suggested content for your :file:`Makefile` that works with the tox and pre-commit configurations:

.. literalinclude:: ../../src/documenteer/storage/localtemplates/technote/Makefile
   :language: make
   :caption: Makefile

Step 11. Update GitHub Actions workflows
----------------------------------------

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

If necessary, commit any changes:

.. prompt:: bash

   git add .github/workflows/ci.yaml
   git commit -m "Update GitHub Actions workflow"

.. note::

   The original Rubin technotes used Travis CI for continuous integration and deployment, but we no longer use that service.
   In that case, you will need to create the :file:`.github/workflows` directory and add the above :file:`ci.yaml` workflow.
   GitHub Actions will automatically start using this workflow.

   If your technote has a :file:`.travis.yml` file, you should delete it:

   .. prompt:: bash

      git rm .travis.yml
      git commit -m "Remove Travis configuration"

Step 12. Add dependabot support
-------------------------------

Dependabot is a service provided by GitHub that generates pull requests when there are new versions of your technote's dependencies.
Set up Dependabot by adding a :file:`.github/dependabot.yml` file:

.. literalinclude:: ../../src/documenteer/storage/localtemplates/technote/dependabot.yml
   :language: yaml
   :caption: .github/dependabot.yml

Commit the changes:

.. prompt:: bash

   git add .github/dependabot.yml
   git commit -m "Add dependabot configuration"

Step 13. Update the README
--------------------------

The README for a legacy-format technote likely has outdated information about how to build the technote.
Here is a suggested README template for technotes in the new format:

.. tab-set::

   .. tab-item:: rst

      .. literalinclude:: _templates/README.rst
         :language: rst
         :caption: README.rst

      Commit any changes:

      .. prompt:: bash

         git add README.rst
         git commit -m "Update README for new technote format"

   .. tab-item:: md

      .. literalinclude:: _templates/README.md
         :language: md
         :caption: README.md

      Commit any changes:

      .. prompt:: bash

         git add README.md
         git commit -m "Update README for new technote format"

Step 14. Merge the migration
----------------------------

At this point, you should have a working technote in the new format.
If you haven't already, push your branch to the GitHub repository and open a pull request.
GitHub Actions will build the technote and publish a preview version that is linked from the ``/v`` path of your technote's website.

If the build works, you can merge the pull request.

If there are build errors, you can reach out to `#dm-docs-support`_ on Slack for help.
Include the repository URL and ideally a link to the pull request or GitHub Actions workflow run that failed.
