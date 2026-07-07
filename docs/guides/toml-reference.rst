##########################
documenteer.toml reference
##########################

Rubin's Sphinx user guide configuration with |documenteer.conf.guide| uses a :file:`documenteer.toml` file, located next to the Sphinx :file:`conf.py` file to configure metadata about the project.
This page describes the schema for this :file:`documenteer.toml` file.
For a step-by-step guide, see :doc:`configuration`.

[project] table
===============

The ``[project]`` table is where most of the project's metadata is set.

|required|

title
-----

|required|

Name of the project, used as titles throughout the documentation site.
The title can be different from the package name, if that's the local standard.

.. code-block:: toml

   [project]
   title = "Documenteer"

.. _guide-project-base-url:

base\_url
---------

|optional| |py-auto|

The root URL of the documentation project, used to set the `canonical URL link rel <https://developer.mozilla.org/en-US/docs/Web/HTML/Attributes/rel>`__, which is valuable for search engines.

.. code-block:: toml

   [project]
   base_url = "https://documenteer.lsst.io"

copyright
---------

|optional|

The copyright statement, which should exclude the "Copyright" prefix.

.. code-block:: toml

   [project]
   copyright = "2015-2022 Association of Universities for Research in Astronomy, Inc. (AURA)"

.. _guide-project-github-url:

github\_url
-----------

|optional| |py-auto|

The URL for the project's GitHub source repository.
When set, a link to the repository is included in the site's header.

.. code-block:: toml

   [project]
   github_url = "https://github.com/lsst-sqre/documenteer"

.. _guide-project-github-default-branch:

github_default_branch
---------------------

|optional|

The default branch on GitHub.
Default is ``main``.
Used in conjunction with the "Edit on GitHub" link, see :ref:`sphinx.show_github_edit_link <guide-project-show-github-edit-link>`.

.. _guide-project-version:

version
-------

|optional| |py-auto|

The project's version, which is set to the standard Sphinx ``version`` and ``release`` configuration variables.

.. _guide-project-openapi:

[project.openapi]
=================

|optional|

Web applications that use OpenAPI can include a ``[project.openapi]`` table in :file:`documenteer.toml` to embed a Redoc_ subsite of the API documentation (see :doc:`openapi`).

.. _guide-project-openapi-doc-path:

doc\_path
---------

|optional|

The docname (without extension) of the page in the Sphinx documentation tree where the Redoc HTML page is built.
Default is ``api``.

.. _guide-project-openapi-openapi-path:

openapi\_path
-------------

|optional|

The path to the OpenAPI specification file, relative to the Sphinx configuration file, :file:`conf.py`.
If ``[project.openapi.generator]`` is set, this is the path where the OpenAPI specification file is generated.

.. _guide-project-openapi-generator:

[project.openapi.generator]
===========================

|optional|

If this table is provided, the OpenAPI specification file is generated from a user-specified Python function.
This is useful for FastAPI and similar applications where the OpenAPI specification is generated from the application code.

.. _guide-project-openapi-generator-function:

function
--------

|required|

The Python function that generates the OpenAPI specification file.
This function must return the OpenAPI specification as a JSON-serialized string.

Specify the function as ``<module>:<function>``.
For example, if the function called ``create_openapi`` is in the :file:`main.py` module of the :file:`example` package, the value would be ``"example.main:create_openapi"``.

.. code-block:: toml

   [project.openapi.generator]
   function = "example.main:create_openapi"

.. _guide-project-openapi-generator-positional-args:

positional\_args
----------------

|optional|

Positional arguments to pass to the function, if required.

.. code-block:: toml

   [project.openapi.generator]
   function = "example.main:create_openapi"
   positional_args = ["arg1", "arg2"]

.. _guide-project-openapi-generator-keyword-args:

keyword\_args
-------------

|optional|

Keyword arguments to pass to the function, if required.

.. code-block:: toml

   [project.openapi.generator]
   function = "example.main:create_openapi"
   keyword_args = {kwarg1 = "value1", kwarg2 = "value2"}

[project.python]
================

|optional|

Projects that use a :file:`pyproject.toml` to set their build metadata can include a ``[project.python]`` table in :file:`documenteer.toml`.
With this, many metadata values are automatically detected — look for |py-auto| badges above.

.. note::

   If a value is directly set, such as :ref:`guide-project-version`, that value will override will override information discovered from the Python project itself.

.. seealso::

   :doc:`pyproject-configuration`

package
-------

|required|

This is the Python project's name, as set in the ``name`` field of the ``[project]`` table in :file:`pyproject.toml`.
*Note that the package name can be different from the Python module name.*
Setting this field actives automatic metadata discovery for Python projects.

.. code-block:: toml

   [project]

   [project.python]
   package = "documenteer"

documentation\_url\_key
-----------------------

|optional|

By default the :ref:`guide-project-base-url` is detected from the ``Homepage`` field in the ``[project.urls]`` table of :file:`pyproject.toml`.
If your documentation's URL is associated with a different field label, set that with ``documentation_url_key``.

github\_url\_key
----------------

|optional|

By default the :ref:`guide-project-github-url` is detected from the ``Source`` field in the ``[project.urls]`` table of :file:`pyproject.toml`.
If your GitHub repository's URL is associated with a different field label, set that with ``github_url_key``.

[sphinx]
========

|optional|

This ``[sphinx]`` table allows you to set a number of Sphinx configurations that you would normally set through the :file:`conf.py` file.

disable_primary_sidebars
------------------------

|optional|

On some pages the default sidebar (on the left) is inappropriate, such as index pages that already contain a table of contents as their main content.
In that case, you can set individual pages or globs (without extensions) of pages that are shown without
the primary sidebar.
The default is ``["index"]`` to remove the sidebar from the homepage.

.. code-block:: toml

   [sphinx]
   disable_primary_sidebars = [
     "**/index",
     "changelog"
   ]

.. note::

   This configuration is for the **primary** sidebar, on the left side, containing side or section-level navigation links.
   To remove the page-level contents sidebar, on the right side, add ``:html_theme.sidebar_secondary.remove:`` to the *page's* file metadata.

exclude
-------

|optional|

A list of file paths, relative to :file:`conf.py`, to exclude from the Sphinx build.
This configuration is often used to prevent file unrelated to the documentation from being accidentally included in the site build.
|documenteer.conf.guide| includes common files and directories, so you may not need to modify this configuration in standard situations.

extensions
----------

|optional|

A list of Sphinx extensions to append to the extensions included in the Documenteer configuration preset (see |documenteer.conf.guide|).
Duplicate extensions are ignored.

Remember that additional packages may need to be added to your project's Python dependencies (such as in a ``requirements.txt`` or ``pyproject.toml`` file).

nitpicky
--------

|optional|

Set to ``true`` to escalate Sphinx warnings to errors, which is useful for leveraging CI to notify you of any syntax errors.
The default is ``false``.

.. code-block:: toml

   [sphinx]
   nitpicky = true

See ``nitpick_ignore`` and ``nitpick_ignore_regex`` for ways to suppress unavoidable errors.

nitpick_ignore
--------------

|optional|

A list of Sphinx warnings to ignore.
Each item is a tuple of two items:

1. ``type``, often the reStructuredText role or directive creating the error/warning.
2. ``target``, often the argument to the reStructuredText role.

.. code-block:: toml

   [sphinx]
   nitpick_ignore = [
     ["py:class", "fastapi.applications.FastAPI"],
     ["py:class", "httpx.AsyncClient"],
     ["py:class", "pydantic.main.BaseModel"],
   ]

This configuration extends the Sphinx ``nitpick_ignore`` configuration.

nitpick_ignore_regex
--------------------

|optional|

A list of Sphinx warnings to ignore, formatted as regular expressions.
Each item is a tuple of two items:

1. ``type``, a regular expression of the warning type.
2. ``target``, a regular expression of the warning target.

.. code-block:: toml

   [sphinx]
   nitpick_ignore_regex = [
     ['py:.*', 'fastapi.*'],
     ['py:.*', 'httpx.*'],
     ['py:.*', 'pydantic*'],
   ]

.. tip::

   Use single quotes for literal strings in TOML.

This configuration extends the Sphinx ``nitpick_ignore_regex`` configuration.

.. _guide-project-rst-epilog-file:

rst_epilog_file
---------------

|optional|

Set this as a path to a reStructuredText file (relative to :file:`documenteer.toml` and :file:`conf.py`) containing substitutions and link targets that are available to all documentation pages.
This configuration sets Sphinx's ``rst_epilog`` configuration.
If set, the file is also included in the Sphinx source ignore list to prevent it from becoming a standalone page.

.. code-block:: toml
   :caption: documenteer.toml

    [sphinx]
    rst_epilog_file = "_rst_epilog.rst"

.. code-block:: rst
   :caption: _rst_epilog.rst

   .. _Astropy Project: https://www.astropy.org

   .. |required| replace:: :bdg-primary-line:`Required`
   .. |optional| replace:: :bdg-secondary-line:`Optional`

See :doc:`rst-epilog`.

python_api_dir
--------------

|optional|

Set this to the directory where Python API documentation is generated, through automodapi_.
The default value is ``api``, which is a good standard for Python projects with a public API.

If the Python API is oriented towards contributors, such as in an application or service, you can change the default:

.. code-block:: toml
   :caption: documenteer.toml

   [sphinx]
   python_api_dir = "dev/api/contents"

.. _guide-sphinx-redirects:

[sphinx.redirects]
==================

|optional|

A table of paths to redirect to other paths. Use this setting to redirect old page locations to the new locations when a documentation site is reorganized.

.. code-block:: toml
   :caption: documenteer.toml

   [sphinx.redirects]
   "old/path" = "new/path"
   "old/path2" = "new/path2"

[sphinx.theme]
==============

|optional|

Configurations related to the Sphinx HTML theme.

.. _guide-project-header-links-before-dropdown:

header_links_before_dropdown
----------------------------

|optional|

Number of links to show in the navigation head before folding extra items into a "More" dropdown.
The default is 5.

If the section titles are long you may need to reduce this number.

.. _guide-project-show-github-edit-link:

show_github_edit_link
---------------------

|optional|

Default is ``true``, so that each page contains a link to edit its source on GitHub.

This configuration requires information about the GitHub repository from these other configurations:

- :ref:`project.github_url <guide-project-github-url>`
- :ref:`project.github_default_branch <guide-project-github-default-branch>`

.. _guide-project-show-last-updated:

show_last_updated
-----------------

|optional|

Default is ``true``, so that each page shows a "Last updated on <date>." timestamp at the bottom of each page.

.. seealso::

   :doc:`/sphinx-extensions/last-updated` for how the date is computed and the extension's
   Sphinx configuration values.

The date is computed from the page's **Git commit history**, not the filesystem modification time (which is meaningless in CI).
It is the most recent commit date across the page's own source file *and* any files the page pulls in with ``include`` or ``literalinclude`` directives, so editing an included snippet updates every page that uses it.
Because the date is the last *commit* date, uncommitted local edits don't change it; a page whose source has never been committed shows no timestamp.

Set this to ``false`` to hide the timestamp:

.. code-block:: toml
   :caption: documenteer.toml

   [sphinx.theme]
   show_last_updated = false

.. important::

   Because the date comes from the Git history, your CI build must check out the **full** commit history.
   With `actions/checkout <https://github.com/actions/checkout>`__, set ``fetch-depth: 0``:

   .. code-block:: yaml
      :caption: .github/workflows/ci.yaml

      - uses: actions/checkout@v6
        with:
          fetch-depth: 0

   A shallow clone (the default) only fetches the most recent commit, so every page would otherwise report the same, incorrect date.
   To avoid publishing misleading data, Documenteer detects a shallow clone, **omits the "Last updated" timestamp from every page**, and emits a single build warning telling you to set ``fetch-depth: 0``.

[sphinx.intersphinx]
====================

|optional|

Configurations related to Intersphinx_ for linking to other Sphinx projects.

[sphinx.intersphinx.projects]
=============================

|optional|

A table of Sphinx projects.
The labels are targets for the :external+sphinx:rst:role:`external` role.
The values are URLs to the root of Sphinx documentation projects.

.. code-block:: toml

   [sphinx.intersphinx.projects]
   sphinx = "https://www.sphinx-doc.org/en/master/"
   documenteer = "https://documenteer.lsst.io"
   python = "https://docs.python.org/3/"

See the Intersphinx_ documentation for details on linking to other Sphinx projects.

[sphinx.linkcheck]
==================

|optional|

Configurations for the ``linkcheck`` builder, which checks the external links in the documentation.

By default, Documenteer replaces Sphinx's built-in linkcheck_ builder with a builder backed by the Ook_ link-check service (the ``documenteer.ext.linkcheckservice`` extension).
Instead of checking every link in-process, the builder submits the project's external links to the service and polls for the results.
The service caches results and retries failing links over time, so documentation builds no longer fail on transient third-party outages.

The service requires a bearer token for the Ook API, read from the ``OOK_TOKEN`` environment variable.
If the token is missing or rejected, the service is unreachable, or the polling budget is exhausted, the build *degrades gracefully* by default: the builder emits a warning and the build finishes with a zero exit status.
Set :ref:`strict <guide-sphinx-linkcheck-strict>` to ``true`` to fail the build on those conditions instead.
Links the service reports as broken always fail the build, regardless of the ``strict`` setting.

.. note::

   **Technotes** use the same service-backed ``linkcheck`` builder, but technotes don't read :file:`documenteer.toml`, so the settings below don't apply to them.
   Instead, the technote configuration preset derives the origin base URL from the ``canonical_url`` setting in the ``[technote]`` table of :file:`technote.toml`, falling back to the technote's handle as ``https://<handle>.lsst.io``.
   The other settings keep their defaults.

   A technote can override any of these settings through the corresponding ``documenteer_linkcheck_*`` configuration values in :file:`conf.py`, after the ``from documenteer.conf.technote import *`` line.
   For example, ``documenteer_linkcheck_use_service = False`` restores Sphinx's built-in linkcheck builder, and ``documenteer_linkcheck_strict = True`` enables strict mode.

ignore
------

|optional|

List of URL regular expressions patterns to ignore checking.
These are appended to the ``linkcheck_ignore`` configuration.

Ignored URLs apply to both the service-backed builder (matching URLs are never submitted to the service) and Sphinx's built-in linkcheck_ builder.

.. _guide-sphinx-linkcheck-use-service:

use_service
-----------

|optional|

Whether to check links with the Ook_ link-check service instead of Sphinx's built-in linkcheck_ builder.
Default is ``true``.

Set this to ``false`` as an escape hatch to restore Sphinx's built-in ``linkcheck`` builder, which checks each link in-process and doesn't require an Ook API token:

.. code-block:: toml

   [sphinx.linkcheck]
   use_service = false

.. _guide-sphinx-linkcheck-service-url:

service_url
-----------

|optional|

Base URL of the Ook API that hosts the link-check service.
Default is ``https://roundtable.lsst.cloud/ook``.

.. _guide-sphinx-linkcheck-poll-budget:

poll_budget
-----------

|optional|

Maximum time, in seconds, to wait for link-check results from the service.
Default is ``300``.

If the budget is exhausted before the service completes the check, the build emits a warning and continues — or fails, if :ref:`strict <guide-sphinx-linkcheck-strict>` is ``true``.

.. _guide-sphinx-linkcheck-strict:

strict
------

|optional|

Whether link-check service problems fail the build.
Default is ``false``: when the service is unavailable (an unreachable service, a missing or rejected ``OOK_TOKEN``, or an exhausted :ref:`poll_budget <guide-sphinx-linkcheck-poll-budget>`), the builder emits a warning and the build finishes with a zero exit status.
Set this to ``true`` to fail the build on those conditions instead:

.. code-block:: toml

   [sphinx.linkcheck]
   strict = true

This setting only gates service *availability* problems.
Links the service reports as broken always fail the build, regardless of this setting.

.. _guide-sphinx-linkcheck-origin-base-url:

origin_base_url
---------------

|optional|

The origin base URL the links are submitted for: the full base URL of the published website (for example, ``https://documenteer.lsst.io``).
The link-check service uses the origin to associate the submitted URLs with the website.
By default the origin is the :ref:`project.base_url <guide-project-base-url>` setting, so most guides don't need to set this override.
The URL is normalized the way the service normalizes origins: the host is lowercased and any trailing slash is stripped.

.. code-block:: toml

   [sphinx.linkcheck]
   origin_base_url = "https://documenteer.lsst.io"
