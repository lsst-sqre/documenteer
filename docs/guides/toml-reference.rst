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

.. _guide-project-title:

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

The root URL of the documentation project, used to set the `canonical URL link rel <https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Attributes/rel>`__, which is valuable for search engines.

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

.. _guide-project-citations:

[[project.citations]]
=====================

|optional|

Sites that are published with a DOI can declare their citations in the ``[[project.citations]]`` array of tables.
Documenteer uses them to make the site a proper DOI landing page: it renders a full bibliographic citation with the DOI as a resolvable ``https://doi.org/`` link, and emits machine-readable citation metadata in the page ``<head>``.

A declared citation is displayed in the :ref:`site footer <guide-footer-citations>` on every page, and with the :ref:`citation-card <guide-citation-card>` directive, which renders it as a card wherever a page asks for one.

That head metadata is what a DOI registration agency, Google Scholar, and Google Dataset Search read.
Every page carries the :ref:`self <guide-project-citations-self>` citation's DOI as a Highwire ``citation_doi`` meta tag (bare) and a Dublin Core ``DC.identifier`` meta tag (as the ``https://doi.org/`` URL), together with a `schema.org <https://schema.org>`__ JSON-LD block that describes the site and the works it cites, following `DataCite's crosswalk <https://doi.org/10.5281/zenodo.7661399>`__ from DataCite metadata to schema.org.
An entry that names a :ref:`page <guide-project-citations-page>` inside the site moves its own metadata to that page instead.
A site that declares no citations emits none of it.

Because it is an *array* of tables, the table header is written with double brackets and repeated once per citation.
A site can cite more than one work — the documentation itself and the dataset it describes, for example — and the order the entries are written in is the order they appear in the site footer.

.. code-block:: toml

   [[project.citations]]
   doi = "10.71929/rubin/2570308"
   label = "Dataset"
   type = "dataset"
   self = true
   note = "Cite the DP2 dataset and this documentation."
   title = "Data Preview 2"
   publisher = "Vera C. Rubin Observatory"
   date = 2025-06-30
   authors = [{ name = "Vera C. Rubin Observatory" }]

Each entry carries two kinds of field.
The *bibliographic* fields (:ref:`doi <guide-project-citations-doi>`, :ref:`type <guide-project-citations-type>`, :ref:`title <guide-project-citations-title>`, :ref:`authors <guide-project-citations-authors>`, :ref:`publisher <guide-project-citations-publisher>`, and :ref:`date <guide-project-citations-date>`) describe the work being cited, and can instead come from a :file:`CITATION.cff` file (see :ref:`cff <guide-project-citations-cff>`).
The *presentation* fields (:ref:`label <guide-project-citations-label>`, :ref:`self <guide-project-citations-self>`, :ref:`page <guide-project-citations-page>`, :ref:`in_footer <guide-project-citations-in-footer>`, and :ref:`note <guide-project-citations-note>`) say how the site displays the citation, and are only ever set here.

.. _guide-project-citations-doi:

doi
---

|optional|

The DOI of the work being cited.
It can be written bare (``10.71929/rubin/2570308``), as a ``https://doi.org/`` URL, or with a ``doi:`` prefix; anything else fails the build.
Either this field or :ref:`cff <guide-project-citations-cff>` must supply a DOI.

.. _guide-project-citations-type:

type
----

|optional|

The kind of work being cited, which decides the schema.org type the site publishes it under in its JSON-LD metadata:

.. list-table::
   :header-rows: 1

   * - ``type``
     - schema.org type
   * - ``"dataset"``
     - `Dataset <https://schema.org/Dataset>`__
   * - ``"article"``
     - `ScholarlyArticle <https://schema.org/ScholarlyArticle>`__
   * - ``"software"``
     - `SoftwareSourceCode <https://schema.org/SoftwareSourceCode>`__
   * - ``"report"``
     - `Report <https://schema.org/Report>`__
   * - ``"other"``
     - `CreativeWork <https://schema.org/CreativeWork>`__

Any other value fails the build.

Set ``type = "dataset"`` on every data product the site publishes: `Dataset <https://schema.org/Dataset>`__ is the type Google Dataset Search indexes, and it is the one that makes a data release discoverable as data rather than as a page about data.

A citation that declares no type says nothing about what the work is, and is published as a `WebSite <https://schema.org/WebSite>`__ if it is the :ref:`self <guide-project-citations-self>` citation and a `CreativeWork <https://schema.org/CreativeWork>`__ otherwise.
The ``self`` entry is typed like any other, so a site that is a data release's landing page declares ``type = "dataset"`` there too.

If :ref:`cff <guide-project-citations-cff>` is set, the file's own ``type`` supplies this field, and setting it here overrides the file's value.

.. _guide-project-citations-label:

label
-----

|optional|

A short label that distinguishes this citation from the site's others, such as ``"Dataset"`` or ``"Paper"``.
It is the label shown on the citation's card, the argument the :ref:`citation-card <guide-citation-card>` directive selects an entry with, and the name a warning about a citation uses.
It is a display string only: what a work *is* is declared with :ref:`type <guide-project-citations-type>`.

.. _guide-project-citations-self:

self
----

|optional|

Whether this is the DOI whose landing page this site is.
Default is ``false``, and at most one entry can set it to ``true``.

The self citation is the one whose metadata the site emits in its ``<head>``, and the one that is shown by default where a citation is displayed.
It is also the one entry that may omit :ref:`title <guide-project-citations-title>`, since the site's own :ref:`project.title <guide-project-title>` is then the title of the work.

.. _guide-project-citations-page:

page
----

|optional|

The page inside this site that is the DOI's registered landing page, written as a Sphinx docname — the source file's path from the documentation root, without its file extension:

.. code-block:: toml

   [[project.citations]]
   doi = "10.71929/rubin/3382539"
   page = "products/catalogs/object"

Default is unset, which means the site as a whole is the landing page.

Setting it moves the entry's machine-readable metadata off every page and onto that one: the claimed page carries this entry's DOI as its Highwire ``citation_doi`` and Dublin Core ``DC.identifier`` meta tags, and a JSON-LD block describing this work at the page's own URL.
Every other page of the site is unaffected and keeps the :ref:`self <guide-project-citations-self>` citation's metadata.
This is what a data release's documentation needs when each of its data products has a DOI of its own that resolves to the product's page; see :ref:`guide-citation-pages`.

The docname may be followed by ``#`` and a fragment identifier, naming a location within the page:

.. code-block:: toml

   [[project.citations]]
   doi = "10.71929/rubin/3382540"
   page = "products/catalogs/object#tap"

Several entries may claim the same page, provided each names a different fragment — two products documented in two sections of one page, for example.
Such a page describes both works in a JSON-LD ``@graph`` and emits *no* ``citation_doi`` or ``DC.identifier`` meta tag, because those tags carry one identifier each and the page is the landing page of more than one DOI.
Two entries that name the same docname *and* the same fragment fail the build.

The claim does not change what the site *displays*: :ref:`citation-card <guide-citation-card>` with no argument still renders the :ref:`self <guide-project-citations-self>` entry, and a page that wants to show its own citation names it by :ref:`label <guide-project-citations-label>`.

A ``page`` naming a docname the project does not contain is a warning, not an error: the entry still appears everywhere else the site shows its citations, but no page carries its landing-page metadata.
That warning carries the subtype ``documenteer.citation_page``, so a site that claims a page it has not written yet can keep it from failing a warnings-as-errors (``-W``) build:

.. code-block:: python

   # conf.py
   suppress_warnings = ["documenteer.citation_page"]

The page's URL comes from :ref:`project.base_url <guide-project-base-url>`.
A site that sets no ``base_url`` cannot know it, so the JSON-LD node falls back to the ``https://doi.org/`` URL, as it does elsewhere; the meta tags are unaffected.

.. _guide-project-citations-in-footer:

in\_footer
----------

|optional|

Whether this citation appears in the :ref:`site footer <guide-footer-citations>`.
Default is ``true`` for the :ref:`self <guide-project-citations-self>` entry and ``false`` for every other, so additional citations are opt-in.
Footer citations appear in the order the entries are written.

.. _guide-project-citations-note:

note
----

|optional|

Free text about when to use this citation, displayed alongside it.

.. code-block:: toml

   [[project.citations]]
   note = "To be used when citing the DP2 dataset and this documentation."

.. _guide-project-citations-title:

title
-----

|optional|

The title of the work being cited.
Required unless :ref:`cff <guide-project-citations-cff>` supplies one, or the entry is the :ref:`self <guide-project-citations-self>` citation — which falls back to the site's :ref:`project.title <guide-project-title>`.

.. _guide-project-citations-authors:

authors
-------

|optional|

The work's authors, in the order they should be credited.
Each author is a table naming either an organization or a person, since the two are cited differently: a person's name is set family-name-first and may be abbreviated by a bibliography style, where an organization's name is kept whole.

An organization is named with ``name``, and optionally its ROR identifier:

.. code-block:: toml

   [[project.citations]]
   authors = [
       { name = "Vera C. Rubin Observatory", ror = "https://ror.org/048g3cy84" },
   ]

A person is named with ``family_name``, and optionally ``given_name``, ``orcid``, and ``affiliation``:

.. code-block:: toml

   [[project.citations]]
   authors = [
       { family_name = "Sick", given_name = "Jonathan", orcid = "https://orcid.org/0000-0003-3001-676X" },
   ]

Setting any author replaces the entire author list that a :ref:`cff <guide-project-citations-cff>` file supplies.

.. _guide-project-citations-publisher:

publisher
---------

|optional|

The organization that published the work.

.. _guide-project-citations-date:

date
----

|optional|

The work's publication date, written as a TOML date (``2025-06-30``).
Only its year appears in a rendered citation.

.. _guide-project-citations-cff:

cff
---

|optional|

The path to a `CITATION.cff <https://citation-file-format.github.io>`__ file that supplies the entry's bibliographic fields, relative to :file:`documenteer.toml`.
Since :file:`documenteer.toml` sits beside :file:`conf.py` in the documentation directory and :file:`CITATION.cff` sits at the repository root, this is usually ``"../CITATION.cff"``.

.. code-block:: toml

   [[project.citations]]
   cff = "../CITATION.cff"
   self = true
   label = "Software"
   note = "Cite this software and its documentation."

A repository that already maintains a :file:`CITATION.cff` for GitHub's "Cite this repository" button has written the bibliographic record down once; pointing at it keeps :file:`documenteer.toml` from restating it.
When the file declares a ``preferred-citation``, that is the citation Documenteer reads, exactly as GitHub renders it.

The file's own ``type`` supplies the entry's :ref:`type <guide-project-citations-type>`, so a repository that describes itself as ``type: software``, or whose preferred citation is an ``article`` or a ``report``, is typed without restating it.
A CFF type that Documenteer has no counterpart for leaves the entry untyped.

Any bibliographic field set alongside ``cff`` overrides the file's value, so a single field can be corrected without abandoning the file:

.. code-block:: toml

   [[project.citations]]
   cff = "../CITATION.cff"
   self = true
   title = "Data Preview 2 Documentation"

A ``cff`` path that names no file, or a file that cannot be read as a citation, fails the build with an error naming the path.

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

.. seealso::

   :doc:`/sphinx-extensions/github-edit-link` for how the edit URL is assembled.

The in-repository path of the documentation is detected automatically from where the Sphinx **source** directory sits in the Git working tree, so there is nothing to configure for it.
Builds that keep :file:`conf.py` outside the source directory — ``sphinx-build -c . docs _build/html``, for instance — link to the right file.

When the documentation isn't being built from a Git checkout (an sdist, or a Docker image built without the :file:`.git` directory) the path can't be determined, so the button is omitted from every page — noted in the build log at the informational level — and the build proceeds.
Such a build does still draw a ``git.subprocess_error`` warning from sphinx-last-updated-by-git, so if you build with ``-W`` see :doc:`/sphinx-extensions/github-edit-link` for the warning to suppress.
To keep the button in that situation, set the path yourself with ``html_context["doc_path"]`` in :file:`conf.py`; see :doc:`/sphinx-extensions/github-edit-link`.

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

.. _guide-sphinx-intersphinx-projects:

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

[sphinx.intersphinx.cache]
==========================

|optional|

Configurations for prefetching intersphinx inventories from the Ook_ inventory cache service (the ``documenteer.ext.intersphinxcache`` extension).

By default, Documenteer prefetches each intersphinx project's object inventory (:file:`objects.inv`) from the Ook_ inventory cache service and rewrites ``intersphinx_mapping`` to point at the locally-written files, so documentation builds no longer depend on third-party site availability.
Only the inventory locations are rewritten — the target URIs are left unchanged, so resolved links still point at the real upstream sites.

Prefetching requires a bearer token for the Ook API, read from the ``OOK_TOKEN`` environment variable.
When the token is unset, the extension is a complete no-op and stock Intersphinx_ behavior is unchanged, so builds still work for projects that haven't configured the token (for example, fork pull requests where secrets are unavailable, or local builds).
When the service fails for an individual inventory (an unauthorized or rejected token, an unreachable service, a server error, or a timeout), that mapping entry is left untouched so Intersphinx_ fetches the origin directly, and the build reports the fallback at the ``INFO`` log level naming the inventory.
The fallback is logged at ``INFO`` rather than as a warning on purpose: Rubin documentation builds run with warnings-as-errors (``-W``), so reporting graceful service degradation as a warning would fail the build.
An Ook outage can never make a build worse than a build without the service.

To avoid re-downloading inventories on every build, Documenteer caches each prefetched :file:`objects.inv` on disk and only revalidates it with Ook after a short time-to-live (see :ref:`disk_cache_ttl <guide-sphinx-intersphinx-cache-disk-cache-ttl>` below).
While a cached inventory is younger than the TTL, it is reused without contacting Ook at all; once the TTL has expired, Documenteer revalidates conditionally with an ``If-None-Match`` request, and a ``304 Not Modified`` reuses the on-disk copy with no inventory body transferred.

.. _guide-sphinx-intersphinx-cache-summary:

The inventory prefetch summary
------------------------------

Once the prefetch is done, Documenteer logs one summary block naming every mapping entry it considered, in :ref:`[sphinx.intersphinx.projects] <guide-sphinx-intersphinx-projects>` order — the order you see in your own configuration file:

.. code-block:: text

   Intersphinx inventory prefetch summary (Ook cache status):
     python    hit           fetched 2026-08-18T17:58:24Z (26 minutes ago)
     sphinx    stale         fetched 2026-08-18T15:24:30Z (3 hours ago)
     numpy     miss          fetched 2026-08-18T18:24:28Z (just now)
     pydantic  hit           fetched 2026-08-09T18:24:30Z (9 days ago)      -> moved
     astropy   served        fetch time unavailable
     safir     disk cache    (Ook was not contacted)
     requests  direct fetch  (Ook could not be reached)

The whole block is logged at ``INFO``, so it never affects a warnings-as-errors (``-W``) build: none of what it reports is yours to fix.
Entries Documenteer doesn't prefetch at all — a local target URI, or an inventory location that's already a local path — get no row.

The second column is how that inventory was obtained.
Three of its values come from Ook, passed through verbatim, and describe the state of *Ook's* copy:

``hit``
   Ook served its cached copy, which was still within its own freshness lifetime.

``stale``
   Ook served its cached copy, which is past its freshness lifetime.
   On its own this is a normal Ook serve, not an error — see :ref:`below <guide-sphinx-intersphinx-cache-stale>`.

``miss``
   Ook had no usable cached copy, so it fetched the inventory from the origin site to answer the request.

The remaining values are Documenteer's own, and describe what the *client* did:

``served``
   Ook answered but sent no cache-status header, so all that's known is that Ook served the inventory.
   This is what an Ook deployment older than the cache-status header looks like.

``disk cache``
   Documenteer's own on-disk TTL fast path answered this entry and Ook was never contacted for it — see :ref:`disk_cache_ttl <guide-sphinx-intersphinx-cache-disk-cache-ttl>`.

``direct fetch``
   The prefetch fell back to the origin: Documenteer left this mapping entry untouched, so Intersphinx_ fetched :file:`objects.inv` from the upstream site itself, exactly as it would without the service.
   The reason is in parentheses on the same row, and the matching per-entry ``INFO`` line above the block carries the full error.

The third column is when Ook last **confirmed** that inventory with its origin site — *not* when the bytes it served to you were downloaded.
A background refresh that the origin answered with ``304 Not Modified`` keeps Ook's stored bytes and still advances this time.
It's reported as the absolute UTC instant, so a row can be correlated with Ook's own logs, followed by a humanized age for eyeballing.
Rows that explain themselves in parentheses (``disk cache`` and ``direct fetch``) report no fetch time, because Ook was either never asked or never served the inventory; an Ook-served row for which the service sent no usable time reads ``fetch time unavailable`` rather than showing a placeholder that would read as an age.

A ``-> moved`` flag marks a row whose configured inventory URL Ook reports as permanently moved.
The destination URL, and what to do about it, are in that entry's own notice rather than in the table; see :ref:`warn_on_permanent_redirect <guide-sphinx-intersphinx-cache-warn-on-permanent-redirect>`.

.. _guide-sphinx-intersphinx-cache-stale:

.. important::

   A ``stale`` row on its own is **not** a problem, and there's nothing to do about it.
   Ook deliberately keeps serving a copy that's past its freshness lifetime while a background job revalidates it, so that a slow or briefly unavailable origin site can't break your build.
   That availability is the entire point of the cache.

   What's worth acting on is ``stale`` **paired with an old fetch time**.
   That combination means Ook's refreshes for that inventory have been failing for as long as the fetch time is old, so the copy you're building against really is drifting from the origin.
   Report it in `#square-docs-support`_ on Slack.

.. _guide-sphinx-intersphinx-cache-use-service:

use_service
-----------

|optional|

Whether to prefetch intersphinx inventories from the Ook_ inventory cache service.
Default is ``true``.

Set this to ``false`` as an escape hatch to disable prefetching so Intersphinx_ fetches every inventory directly from its origin site:

.. code-block:: toml

   [sphinx.intersphinx.cache]
   use_service = false

With ``use_service = false`` the service is never contacted, even when an ``OOK_TOKEN`` is set.

.. _guide-sphinx-intersphinx-cache-service-url:

service_url
-----------

|optional|

Base URL of the Ook API that hosts the intersphinx inventory cache service.
Default is ``https://roundtable.lsst.cloud/ook``.

.. _guide-sphinx-intersphinx-cache-disk-cache-ttl:

disk_cache_ttl
--------------

|optional|

How long, in seconds, a prefetched inventory on disk is reused before Documenteer revalidates it with the Ook_ service.
Default is ``600`` (10 minutes).

While a cached :file:`objects.inv` is younger than the TTL, Documenteer reuses it as-is and makes no request to Ook, so rapid successive local rebuilds skip the round-trip entirely.
Once the TTL has expired, Documenteer revalidates the inventory conditionally: it sends the ETag it stored alongside the cached file as an ``If-None-Match`` header, and if Ook answers ``304 Not Modified`` the on-disk copy is reused with no inventory body transferred and its TTL window restarts.
A ``200 OK`` response replaces the cached inventory.

Set ``disk_cache_ttl`` to ``0`` to disable this fast path so every build revalidates with Ook:

.. code-block:: toml

   [sphinx.intersphinx.cache]
   disk_cache_ttl = 0

The TTL governs only the client-to-Ook hop; whether Ook's own cached copy is current relative to the origin site remains Ook's concern.

.. _guide-sphinx-intersphinx-cache-warn-on-permanent-redirect:

warn_on_permanent_redirect
--------------------------

|optional|

Whether to report a permanently-moved intersphinx inventory URL as a Sphinx warning rather than at the ``INFO`` log level.
Default is ``false``.

When the Ook_ service reports that one of your configured inventory URLs now redirects permanently to a new location, Documenteer tells you so in the build log, naming the mapping key, the URL you configure, where it now lives, and the ``[sphinx.intersphinx.projects]`` entry to update.
By default that notice is logged at ``INFO``: the move originates upstream, outside your control, and Rubin documentation builds run with warnings-as-errors (``-W``), so warning about it would fail your builds on a third party's schedule.

Set this to ``true`` if you would rather your build fail than carry a stale inventory URL:

.. code-block:: toml

   [sphinx.intersphinx.cache]
   warn_on_permanent_redirect = true

The setting escalates only that one notice.
The inventory summary block stays at ``INFO`` either way, so opting in never turns a block of pure status reporting into a build failure, and prefetching is unaffected — the mapping entry is still rewritten to the locally cached inventory whether or not escalation is enabled.

The escalated notice carries the warning subtype ``documenteer.intersphinx_permanent_redirect``, so you can silence a move you already know about — one you can't act on yet, for instance — while keeping the warning for every other inventory:

.. code-block:: python

   # conf.py
   suppress_warnings = ["documenteer.intersphinx_permanent_redirect"]

Note that Ook reports the redirect chain it observed at *its* last successful fetch of the inventory, not at your build time.

[sphinx.linkcheck]
==================

|optional|

Configurations for the ``linkcheck`` builder, which checks the external links in the documentation.

By default, Documenteer replaces Sphinx's built-in linkcheck_ builder with a builder backed by the Ook_ link-check service (the ``documenteer.ext.linkcheckservice`` extension).
Instead of checking every link in-process, the builder submits the project's external links to the service and polls for the results.
The service caches results and retries failing links over time, so documentation builds no longer fail on transient third-party outages.

The service requires a bearer token for the Ook API, read from the ``OOK_TOKEN`` environment variable.
If the token is missing or rejected, the builder *falls back* to Sphinx's built-in in-process linkcheck_ builder in every mode, so link checking still runs for projects that haven't configured the token (for example, fork pull requests where secrets are unavailable, or CI that doesn't forward the token).
The built-in check's own result then decides the build's exit status.
If instead the service is unreachable or the polling budget is exhausted, the build falls back the same way by default: the builder reports the service problem at the ``INFO`` log level and checks the links in-process.
An outage therefore costs the build time — every link is visited from the machine running the build, with none of the service's caching or retry buffering — rather than costing it link checking, and broken links the in-process check finds fail the build as they always do.
Set :ref:`strict <guide-sphinx-linkcheck-strict>` to ``true`` to fail the build on the service problem itself instead.
Links the service reports as broken always fail the build, regardless of the ``strict`` setting.

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

With ``use_service = false`` the built-in builder is selected outright and the service is never contacted, even when an ``OOK_TOKEN`` is set.
This differs from the automatic token fallback under the default ``use_service = true``, where the builder uses the service when a token works and only falls back to the built-in in-process check when the ``OOK_TOKEN`` is missing or rejected.

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

If the budget is exhausted before the service completes the check, the build falls back to Sphinx's built-in in-process linkcheck_ builder — or fails, if :ref:`strict <guide-sphinx-linkcheck-strict>` is ``true``.

.. _guide-sphinx-linkcheck-strict:

strict
------

|optional|

Whether genuine link-check service problems fail the build.
Default is ``false``: when the service is unreachable or the :ref:`poll_budget <guide-sphinx-linkcheck-poll-budget>` is exhausted, the builder reports the problem at the ``INFO`` log level and falls back to Sphinx's built-in in-process linkcheck_ builder, whose own result then decides the exit status.
Nothing is skipped, so an outage doesn't silently stop checking your links; it does mean a build during one takes as long as a full in-process link check, and broken links that check finds fail the build.

Set this to ``true`` to fail the build on the service problem itself instead, with no fallback:

.. code-block:: toml

   [sphinx.linkcheck]
   strict = true

Use it when a substitute check isn't what you want — when the point of the build is that the service was consulted, or when you'd rather see an outage immediately than pay for the in-process check.

This setting only gates genuine service *availability* problems.
A missing or rejected ``OOK_TOKEN`` is not one of them: rather than failing, the builder falls back to Sphinx's built-in in-process linkcheck_ builder in every mode (including under ``strict``), so link checking still runs.
Links the service reports as broken always fail the build, regardless of this setting.

.. _guide-sphinx-linkcheck-recheck-unverified:

recheck_unverified
------------------

|optional|

Whether URLs the service couldn't verify from its own vantage point are rechecked from the build's.
Default is ``true``.

Two of the service's verdicts rest on evidence nobody actually obtained about the link:

**Blocked URLs.**
Some sites sit behind a bot-protection edge (typically Cloudflare) that answers the service's requests with a ``403`` no matter how ordinary the request is.
The service can't tell such a URL apart from one that's genuinely refusing everyone, so it reports the URL as ``blocked``: a caveat rather than a failure, never counted as broken.

**URLs the service couldn't reach at all.**
When a request gets no response — a TLS chain the service can't build, a connection the far end drops, a name it can't resolve — the service reports the URL ``broken`` with no HTTP status code.
That verdict *does* fail the build, and it's the one worth the most scrutiny: nothing about it is specific to the link rather than to the service's own network.

A documentation build usually runs somewhere else entirely — a GitHub Actions runner the same site is happy to serve, with its own trust store and its own route — so the build can often settle what the service couldn't.
Documenteer rechecks exactly those URLs, and no others, from the machine running the build, sending the same request Sphinx's built-in linkcheck_ builder would send.
The checks are sequential with a short delay between them, so a handful of rechecks never arrives at a site as a burst.

A ``broken`` result that *does* carry a status code is never rechecked.
That's a definite answer from the server itself — a ``404`` is a ``404`` from every vantage point — and a second opinion has no standing to overturn it.

What the build observes is merged into that same build's report:

- A URL the build resolves is reported ``ok`` (or ``redirected``, if it works only through a permanent redirect), and its bot-protection caveat, or the failure the service couldn't reproduce, clears.
- A URL that answers the build with a definite failure (a ``404``, say) is reported ``broken``, with the build's own evidence — which fails the build, as any broken link does.
- A URL blocked from the build's vantage point too keeps its ``blocked`` status, its caveat, and the service's own evidence: the recheck settled nothing, so nothing is rewritten.
- So does a URL that answers the build with nothing at all — a timeout, a connection reset, a DNS failure. Bot protection doesn't always answer with a status code, and a runner's network blip is not evidence about a link, so only a failure the server itself answered with is allowed to turn the service's caveat into a build failure.
- A URL the service couldn't reach and the build can't reach either stays ``broken`` and still fails the build. Two vantage points coming back empty-handed isn't proof the link works; its detail line says both looked, so you can tell it apart from one nobody checked twice.

The :file:`linkcheck.json` artifact reflects the merged view, and flags each result the build rechecked for itself with ``locally_rechecked``.

The observations the build actually obtained are also contributed back to the service, so the next project to reference the URL benefits from them — see :ref:`guide-sphinx-linkcheck-contributions`, below.

Set this to ``false`` to skip the recheck, and the contribution along with it, and report the service's verdict as-is:

.. code-block:: toml

   [sphinx.linkcheck]
   recheck_unverified = false

.. _guide-sphinx-linkcheck-contributions:

Contributing rechecked results back to the service
--------------------------------------------------

A build that settles a URL the service could only report as ``blocked`` knows something the service can't learn from its own vantage point.
Documenteer hands that knowledge back: whenever the :ref:`recheck <guide-sphinx-linkcheck-recheck-unverified>` finds blocked URLs, the builder posts what it observed — successes and failures alike, since a URL that's blocked from the runner too is evidence as well — to the check's contributions endpoint on the Ook_ API.
Each contributed result carries the same evidence the recheck merged into this build's report: the final status code, any redirect that was followed, and the error text when the request failed outright.
A URL that answered the build with nothing at all is one exception: a contribution is applied to state every other project's build reads, so an observation the build wouldn't apply to its own report — a timeout or a dropped connection settles nothing about a link — isn't handed on as shared evidence either.
The other is a URL the service reported ``broken``: the service only applies a contributed result to a URL its own stored state has as ``blocked``, so an observation for one it reported broken would come back rejected, and Documenteer withholds it rather than sending it to be refused.
Those URLs are still rechecked, and what the build observes still informs this build's own report.
A build whose links the service settled on its own has nothing to contribute, and doesn't so much as mint a token — which is the overwhelmingly common case.

Contributions are attested with a `GitHub Actions OIDC id token <https://docs.github.com/en/actions/concepts/security/openid-connect>`__ rather than a shared secret, so the service records the verified claims of the workflow run — the repository it ran in — as the provenance of every result it applies.
Documenteer mints that token with the configured :ref:`service_url <guide-sphinx-linkcheck-service-url>` as its audience, which scopes it to one deployment: a token minted for a development Ook can't be replayed against production, and there's no separate audience setting to keep in sync.
The request also carries the same ``OOK_TOKEN`` bearer the rest of the link check uses; both are required.
Alongside the results it describes the run — the repository and run URL from the Actions environment, and the Documenteer version that made the observations — but those fields are advisory only, and the service takes the provenance it records from the token's claims instead.

Contributing needs the ``id-token: write`` permission, because that's what makes GitHub expose the OIDC token endpoint to the job:

.. code-block:: yaml
   :caption: .github/workflows/ci.yaml

   jobs:
     docs:
       runs-on: ubuntu-latest
       permissions:
         contents: read
         id-token: write  # contribute link-check results to Ook
       steps:
         # ...

.. important::

   A **reusable workflow** can't ask for a permission of its own: permissions come from the calling job, and a called workflow can only narrow them.
   If your documentation build runs through a shared workflow, add ``permissions: id-token: write`` to the job in your own repository that calls it, and confirm with that workflow's maintainers that its build job passes the permission through rather than narrowing it away.
   Both sides have to be in place before a contribution can be attested.

A run that contributes says so in its build log, first from the recheck and then from the contribution::

   Local recheck: 3 verified, 1 still blocked, 0 failing
   Contributed 4 link-check results to lsst-sqre/documenteer (4 accepted, 0 rejected)

Nothing about a contribution can fail the build.
It improves somebody else's future build, so it's never allowed to cost this one — not even under :ref:`strict <guide-sphinx-linkcheck-strict>`, which gates service *availability* problems only.
Every way it can go wrong is reported at the ``INFO`` log level rather than as a warning, which is what keeps that promise for a build run with ``-W`` (warnings as errors), where a warning is a failure:

- Where no id token can be minted, the local recheck still runs and still informs this build's report, and only the contribution is skipped, with a note naming the ``id-token: write`` permission — because the absence looks identical whether the build is on a laptop, where there's nothing to fix, or in a workflow that never asked for the permission, where there's one line to add.
- The service applies a batch entry by entry, so an entry it declines (a URL that isn't one of the check's members, say, or one that isn't ``blocked`` because its own vantage point already settled it) is reported per URL with the service's reason, and the rest of the batch still applies.
- A batch that can't be delivered at all is retried for the failures the service documents as retryable — a ``502`` while it can't reach GitHub's signing keys, and connection failures — up to three times after the first attempt, on a backoff that starts at half a second and doubles.
  If those attempts are exhausted, the builder reports it and moves on; the build's exit status is unchanged.
  A response that would fail identically however often it's sent, such as a ``422`` for a batch the service won't accept, is reported the same way on its first response instead of being retried.

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
