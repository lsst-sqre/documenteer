#####################################
Migrate legacy Sphinx technical notes
#####################################

Introduced in November 2023, Rubin Observatory has a new technical note format for Markdown and reStructuredText documents, based on the Sphinx_ and the `Technote <https://technote.lsst.io>`__ Python packages.
If your started writing your technical note before November 2023, it is likely in the legacy Sphinx format.
You can tell if your technical note is in the legacy format if it has a :file:`manifest.yaml` file.
If you are continuing to write such a technical note, you should migrate it to the new format to take advantage of new features.
This page provides a guide to migrating your technical note to the new format.

To get started on your migration, be sure to have your technote repository checked-out locally.
Work on a ticket branch, `per the Developer Guide <https://developer.lsst.io/work/flow.html>`__, so you can check your work with a pull request before merging to the ``main`` branch.

Step 1. Create a technote.toml file
===================================

The :file:`technote.toml` file replaces the original :file:`manifest.yaml` file.
This new file provides both metadata and Sphinx configuration for your document.

Here is a simple :file:`technote.toml` file to get you started:

.. code-block:: toml

   [technote]
   id = "EXAMPLE-000"
   series_id = "EXAMPLE"
   canonical_url = "https://example-000.lsst.io/"
   github_url = "https://github.com/lsst/example-000"
   github_default_branch = "main"
   date_created = "2015-11-18"
   date_updated = "2023-11-01"

   [[technote.authors]]
   name = { given_names = "Drew", family_names = "Developer" }
   orcid = "https://orcid.org/0000-0001-2345-6789"
   affiliations = [
       { name = "Rubin Observatory", ror = "https://ror.org/048g3cy84" }
   ]

Add this file to your repository and commit it:

.. prompt:: bash

   git add technote.toml
   git commit -m "Add technote.toml file"

Step 2. Update conf.py
======================

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
=================================

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
-------------

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
-------------------------------------------------

The original technote format used a ``note`` directive to describe whether the document was a draft or deprecated.
Now this status metadata is structured in :file:`technote.toml`.
Delete the ``note`` directive and add the status information to :file:`technote.toml` following :doc:`document-status`.

Format the abstract/summary with the abstract directive
-------------------------------------------------------

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
------------------------------

If your technote makes references to other documents with roles like :rst:dir:`cite`, you'll need a reference section to display the bibliography.
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
------------------

.. tab-set::

   .. tab-item:: rst

      .. prompt:: bash

         git add index.rst
         git commit -m "Reformat index.rst for new technote format"

   .. tab-item:: md

      .. prompt:: bash

         git add index.md
         git commit -m "Reformat index.md for new technote format"

Step 4. Delete manifest.yaml
============================

At this point, all relevant metadata about the technote is in :file:`technote.toml` or :file:`index.rst`/:file:`index.md`.
Delete the deprecated :file:`manifest.yaml` file:

.. prompt:: bash

   git rm manifest.yaml
   git commit -m "Remove manifest.yaml file"

Step 5. Delete the lsstbib/ directory
=====================================

The legacy technote format vendored Rubin BibTeX bibliography files from https://github.com/lsst/lsst-texmf.
The new technote format automatically downloads and caches these files so that you no longer need to commit them into your repository.
Delete the :file:`lsstbib` directory:

.. prompt:: bash

   git rm -r lsstbib
   git commit -m "Remove lsstbib/ directory"

Step 6. Update .gitignore
=========================

The new technote format introduces additional directories that should be ignored by Git.
Ensure at least the following paths are included in the :file:`.gitignore` file:

.. code-block:: text
   :caption: .gitignore

   _build
   .technote
   .tox
   venv
   .venv

.. prompt:: bash

   git add .gitignore
   git commit -m "Update .gitignore file"

Step 7. Set up pre-commit hooks
===============================

Pre-commit_ is a Python package that runs validation and formatting checks on your technote's repository before you commit.
Although it is not required, it's highly recommended that you set up pre-commit hooks for your technote.
To start, add a :file:`.pre-commit-config.yaml` file:

.. code-block:: yaml
   :caption: .pre-commit-config.yaml

   repos:
     - repo: https://github.com/pre-commit/pre-commit-hooks
       rev: v4.5.0
       hooks:
         - id: trailing-whitespace
         - id: check-yaml
         - id: check-toml

Commit any changes:

.. prompt:: bash

   git add .pre-commit-config.yaml
   git commit -m "Add pre-commit configuration"

.. tip::

   You can add additional pre-commit hooks to this file to suite your needs.
   See Pre-commit's `directory of available hooks <https://pre-commit.com/hooks.html>`__ for ideas.

Step 6. Update requirements.txt
===============================

The Python dependencies for your technote are listed in a :file:`requirements.txt` file that should now look like this:

.. code-block:: text
   :caption: requirements.txt

   documenteer[technote]>=1.0.0,<2.0.0

Commit any changes:

.. prompt:: bash

   git add requirements.txt
   git commit -m "Update requirements.txt file"

.. note::

   If your technote has additional dependencies listed, you can reach out to `#dm-docs-support`_ on Slack if you are unsure whether they are part of the Sphinx build process or separate packages needed for any custom document preprocessing.

Step 7. Add a tox.ini file
==========================

Tox_ is a tool for running Python programs in dedicated virtual environments.
This makes your local technote builds more reproducible by separating the technote's dependencies from your system and other projects.

This is the recommend tox configuration to start with:

.. code-block:: ini
   :caption: tox.ini

   [tox]
   environments = html
   isolated_build = True

   [testenv]
   skip_install = true
   deps =
       -rrequirements.txt

   [testenv:html]
   commands =
      sphinx-build --keep-going -n -W -T -b html -d {envtmpdir}/doctrees . _build/html

   [testenv:linkcheck]
   commands =
      sphinx-build --keep-going -n -W -T -b linkcheck -d {envtmpdir}/doctrees . _build/linkcheck

   [testenv:lint]
   commands =
      pre-commit run --all-files

Step 7. Update the Makefile
===========================

The :file:`Makefile` file provides a simple entrypoint for building your technote and performing other common tasks.
This is the suggested content for your :file:`Makefile` that works with the tox and pre-commit configurations:

.. code-block:: Makefile

   .PHONY:
   init:
   	pip install tox pre-commit
   	pre-commit install

   .PHONY:
   html:
   	tox run -e html

   .PHONY:
   lint:
   	tox run -e lint,link-check

   .PHONY:
   clean:
   	rm -rf _build
   	rm -rf .technote
   	rm -rf .tox

Step 8. Update GitHub Actions workflows
=======================================

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

Step 9. Add dependabot support
==============================

Dependabot is a service provided by GitHub that generates pull requests when there are new versions of your technote's dependencies.
Set up Dependabot by adding a :file:`.github/dependabot.yml` file:

.. code-block:: yaml
   :caption: .github/dependabot.yml

   version: 2
   updates:
     - package-ecosystem: "github-actions"
       directory: "/"
       schedule:
         interval: "weekly"

     - package-ecosystem: "pip"
       directory: "/"
       schedule:
         interval: "weekly"

Commit the changes:

.. prompt:: bash

   git add .github/dependabot.yml
   git commit -m "Add dependabot configuration"

Step 10. Update the README
==========================

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

Step 11. Merge the migration
============================

At this point, you should have a working technote in the new format.
If you haven't already, push your branch to the GitHub repository and open a pull request.
GitHub Actions will build the technote and publish a preview version that is linked from the ``/v`` path of your technote's website.

If the build works, you can merge the pull request.

If there are build errors, you can reach out to `#dm-docs-support`_ on Slack for help.
Include the repository URL and ideally a link to the pull request or GitHub Actions workflow run that failed.
