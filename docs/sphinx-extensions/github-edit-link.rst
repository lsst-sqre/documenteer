.. _documenteer-ext-githubeditlink:

######################
"Edit on GitHub" links
######################

Documenteer's ``documenteer.ext.githubeditlink`` extension resolves the in-repository path that pydata-sphinx-theme's "Edit on GitHub" button links to.
It determines where the Sphinx **source** directory sits inside the Git working tree and publishes that path as the ``doc_path`` value in the HTML context.

In the user-guide preset the link is not rendered in the theme's default position in the right sidebar; instead it appears in the :ref:`"Help improve this page" box <guide-improve-this-page>` at the bottom of each page, below the previous/next page links, alongside the :ref:`Git-derived last-modified timestamp <documenteer-ext-lastmodified>`.
Individual pages can hide the box with the :ref:`hide_content_footer metadata field <guide-improve-this-page>`.

.. tip::

   If you use Documenteer's user-guide configuration preset, this extension is already enabled and the link is shown by default.
   Toggle it with the :ref:`show_github_edit_link <guide-project-show-github-edit-link>` setting in :file:`documenteer.toml`; you don't need to edit :file:`conf.py`.

How the edit URL is built
=========================

pydata-sphinx-theme assembles the edit URL from several HTML context values:

.. code-block:: text

   {github_url}/{github_user}/{github_repo}/edit/{github_version}/{doc_path}{file_name}

The user-guide preset fills in ``github_user``, ``github_repo``, and ``github_version`` from the :ref:`project.github_url <guide-project-github-url>` and :ref:`project.github_default_branch <guide-project-github-default-branch>` settings in :file:`documenteer.toml`.

``file_name`` is supplied by the theme as the page's document name plus its source suffix — for example :file:`index.rst`.
That name is relative to the Sphinx **source** directory, so ``doc_path`` has to be the source directory's own path within the Git working tree for the two halves to join into a real file path.
This extension computes that path.

Why an extension rather than :file:`conf.py`
============================================

The rest of the "Edit on GitHub" context is assembled while :file:`conf.py` is executed, but ``doc_path`` cannot be.
At that moment there is no Sphinx application yet, and therefore no source directory to consult; the only path available is the current working directory, which Sphinx sets to the directory holding :file:`conf.py` — the *configuration* directory.

For many projects the configuration and source directories are the same, and the distinction doesn't matter.
They differ whenever a build passes ``-c``:

.. code-block:: shell

   sphinx-build -b html -c . docs _build/html

Here the configuration directory is the repository root while the source directory is :file:`docs/`.
A ``doc_path`` taken from the configuration directory would produce a URL that looks plausible but points at a file that doesn't exist.

This extension therefore computes ``doc_path`` from the source directory at Sphinx's ``config-inited`` event — the earliest point where the source directory is known.
That is also the safest point at which to *switch the button off*, because a theme may copy ``html_theme_options`` when the builder initializes, and a change made after that copy wouldn't reach the template.

Overriding the detected path
============================

Auto-detection covers every layout Rubin projects are known to use, but you can set ``doc_path`` yourself in :file:`conf.py` to override it:

.. code-block:: python
   :caption: conf.py

   html_context["doc_path"] = "docs"

When ``doc_path`` is already set, the extension uses that value and doesn't consult Git at all.
The button therefore keeps working outside a Git checkout — supplying the path answers the question that auto-detection would have used the working tree to answer.

This is the escape hatch for source layouts that a path within the working tree can't describe, such as a generated source directory, or documentation published from a different repository than the one being built.

Builds outside a Git checkout
=============================

The path can only be derived from a Git working tree.
When the source directory isn't inside one — an sdist, a vendored documentation tree, or a Docker image built without the :file:`.git` directory — the extension omits the "Edit on GitHub" button from every page and notes this in the build log at the informational level.

The message is deliberately *not* a warning: building outside a checkout is legitimate, and a warning would fail any build run with ``-W`` (which turns warnings into errors).

.. note::

   This extension stays quiet, but it isn't the only part of the user-guide stack that reads Git.
   The preset also loads `sphinx-last-updated-by-git <https://github.com/mgeier/sphinx-last-updated-by-git>`__ (through sphinx-sitemap), which *does* warn when it can't read the history:

   .. code-block:: text

      WARNING: Error getting data from Git (no "last updated" dates will be shown
      for source files from …): fatal: not a git repository [git.subprocess_error]

   A project that builds with ``-W`` outside a Git checkout therefore needs to suppress that warning as well:

   .. code-block:: python
      :caption: conf.py

      suppress_warnings = ["git.subprocess_error"]

   Without ``-W`` the warning is harmless and the build succeeds either way.

Reference
=========

The user-guide configuration preset enables this extension automatically.
To use it in a standalone Sphinx project, add ``"documenteer.ext.githubeditlink"`` to the extensions list in :file:`conf.py` and provide the repository context that pydata-sphinx-theme expects:

.. code-block:: python
   :caption: conf.py

   extensions = ["documenteer.ext.githubeditlink", ...]

   html_theme = "pydata_sphinx_theme"
   html_theme_options = {
       "use_edit_page_button": True,
   }
   html_context = {
       "github_user": "lsst-sqre",
       "github_repo": "documenteer",
       "github_version": "main",
   }

The extension fills in ``doc_path`` itself, so you don't need to provide it — but it honors the value if you do (see `Overriding the detected path`_).
It takes no configuration of its own, and is inert unless ``use_edit_page_button`` is enabled.
