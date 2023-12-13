####################################
Edit a technote on your own computer
####################################

For most writers, the best way to edit a technote is on a computer you control and can install software on.
This might be your own laptop, or a computer account in the cloud like the Rubin Science Platform or GitHub Codespaces.

If you don't already have a technote repository set up, :doc:`start-a-technote` first.

Set up
======

Clone the repository
--------------------

First clone the GitHub repository containing your technote.
In a terminal, run :samp:`git clone https://github.com/{repo}`.

The URL for the repository is provided by the Slack bot when you created the technote.

Initialize the Python environment
---------------------------------

In a terminal, from the root of the repository, run:

.. prompt:: bash

   make init

This installs two Python packages: tox_ and pre-commit_.
Both of these tools create their own isolated Python environments to actually run the document builder and linter in.
Because of that, you don't need to rely on a specific Rubin Conda environment to build technotes.

.. important::

   Tox and pre-commit generally use the Python that they were installed with.
   Documenteer requires Python 3.11 or later.
   To check what version of Python you have, run:

   .. prompt:: bash

      python --version

Build the technote's web page
-----------------------------

In a terminal, from the root of the repository, run:

.. prompt:: bash

   make html

This will build the technote's web page and put it in the :file:`_build/html` directory.
On a Mac, you can open the page in your browser:

.. prompt:: bash

   open _build/html/index.html

Under the hood, :command:`make html` invokes tox_ and its `html` environment to build the technote in an isolated Python environment.

Running linters
---------------

Technote projects are configured to use linters to check for common issues.

To run the linters on-demand, run:

.. prompt:: bash

   make lint

That command runs both the Pre-commit_ hooks and the link checker.
If you ran :command:`make init`, the Pre-commit hooks will also run automatically before every Git commit.

Resetting your environment
--------------------------

Both the Python environment and the web site build are cached.
You might want to reset those caches if the website is not building properly, or if you suspect that the Python environment is out of date (for example, a new version of Documenteer is available).
To delete the caches, run:

.. prompt:: bash

   make clean

Then run :command:`make html` again to rebuild the website in a fresh environment.

.. tip::

   You can be more selective about what you clean.
   If you only want to delete the website cache, but keep all the installed Python packages in the Python environment, run:

   .. prompt:: bash

      rm -rf _build

Related documentation
---------------------

- :doc:`edit-on-github`
