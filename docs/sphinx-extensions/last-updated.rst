.. _documenteer-ext-lastmodified:

##############################
"Last updated" page timestamps
##############################

Documenteer's ``documenteer.ext.lastmodified`` extension adds a "Last updated on <date>." timestamp to the bottom of each page's article body.
The date is derived from the page's **Git commit history** rather than the filesystem modification time, which is meaningless in CI where checkouts have arbitrary timestamps.
The extension is theme-agnostic: it stores the formatted date in each page's ``last_updated`` template context variable, which pydata-sphinx-theme renders through its built-in ``last-updated`` component.
It is also the single source of truth for the page's last-modified date in the HTML ``<head>``, where it emits the same Git date as Open Graph, Dublin Core, and Schema.org metadata (see `HTML metadata`_).

.. tip::

   If you use Documenteer's user-guide configuration preset, this extension is already enabled and the timestamp is shown by default.
   Toggle it with the :ref:`show_last_updated <guide-project-show-last-updated>` setting in :file:`documenteer.toml`; you don't need to edit :file:`conf.py`.

How the date is computed
========================

The timestamp is the most recent commit date across the page's own source file *and* any files it pulls in with the ``include`` or ``literalinclude`` directives.
Editing an included snippet therefore updates the timestamp on every page that uses it.

Because the date is the last *commit* date:

- Uncommitted local edits don't change it.
- A page whose source has never been committed shows no timestamp.
- Generated pages without a source document (such as the search page and general index) show no timestamp.

HTML metadata
=============

Besides the visible footer timestamp, the extension writes the **same Git commit date** into the page's HTML ``<head>`` as three machine-readable signals, so that downstream consumers all agree:

- ``<meta property="article:modified_time">`` — the `Open Graph <https://ogp.me/>`__ property used by social-media link previews.
- ``<meta name="dcterms.modified">`` — the `Dublin Core <https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#modified>`__ modification date.
- A `Schema.org <https://schema.org/dateModified>`__ ``dateModified`` field inside a JSON-LD ``<script type="application/ld+json">`` block (typed as ``WebPage``).

In addition, pydata-sphinx-theme renders a ``<meta name="docbuild:last-update">`` tag from the same ``last_updated`` context value.

.. note::

   sphinx-sitemap (enabled by the user-guide preset) auto-loads `sphinx-last-updated-by-git <https://github.com/mgeier/sphinx-last-updated-by-git>`__ to populate the sitemap's ``<lastmod>`` entries.
   That extension runs its *own* Git computation and would otherwise emit a second, potentially divergent ``article:modified_time`` tag.
   To keep this extension the single source of truth, the user-guide preset sets ``git_last_updated_metatags = False``, which silences the duplicate Open Graph tag while leaving the sitemap behavior intact.

Full Git history is required
============================

The date comes from Git, so the build must have the **full** commit history.

.. important::

   With `actions/checkout <https://github.com/actions/checkout>`__, set ``fetch-depth: 0``:

   .. code-block:: yaml
      :caption: .github/workflows/ci.yaml

      - uses: actions/checkout@v6
        with:
          fetch-depth: 0

   A shallow clone (the default) only fetches the most recent commit, so every page would otherwise report the same, incorrect date.
   To avoid publishing misleading data, Documenteer detects a shallow clone, omits the timestamp from every page, and emits a single build warning.

Reference
=========

Extension module
----------------

The user-guide configuration preset enables this extension automatically.
To use it in a standalone Sphinx project, add ``"documenteer.ext.lastmodified"`` to the extensions list in :file:`conf.py` and render the ``last_updated`` context value.
With pydata-sphinx-theme, add the ``last-updated`` component to the article footer:

.. code-block:: python
   :caption: conf.py

   extensions = ["documenteer.ext.lastmodified", ...]

   html_theme = "pydata_sphinx_theme"
   html_theme_options = {
       "article_footer_items": ["last-updated"],
   }

Configurations
--------------

Set these configurations in the Sphinx :file:`conf.py` file.

.. _documenteer-last-modified-enabled-conf:

documenteer\_last\_modified\_enabled
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Whether to compute and show the "Last updated" timestamp.
A boolean that defaults to `True`.
In the user-guide preset this is set automatically from the :ref:`show_last_updated <guide-project-show-last-updated>` field in :file:`documenteer.toml`.

.. _documenteer-last-modified-date-format-conf:

documenteer\_last\_modified\_date\_format
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``strftime``-style format string for the date.
Defaults to ``"%b %d, %Y"`` (for example, ``Jun 16, 2026``).
The date is formatted with Sphinx's date machinery, so it respects the build's ``language`` setting.

.. code-block:: python
   :caption: conf.py

   documenteer_last_modified_date_format = "%Y-%m-%d"
