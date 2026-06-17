"""Sphinx extension that adds a "Last updated" timestamp to each page based
on the page's Git commit history.

For each HTML output page, this extension computes the most recent commit
datetime across the page's source file *and* any files that the page pulls in
via ``include``/``literalinclude`` directives.

That datetime is exposed to the page template in three forms:

- ``last_updated`` -- the date formatted with
  ``documenteer_last_modified_date_format`` in the *commit's* timezone offset.
  Sphinx emits this as the ``docbuild:last-update`` meta tag, and it is the
  value any theme-agnostic ``last-updated`` rendering uses.
- ``documenteer_last_modified_iso`` -- the canonical UTC ISO 8601 timestamp
  (for example ``2024-06-01T00:00:00+00:00``).
- ``documenteer_last_modified_date`` -- the UTC date as ``YYYY-MM-DD`` (for
  example ``2024-06-01``).

Documenteer's user-guide preset overrides pydata-sphinx-theme's
``last-updated`` component (``src/documenteer/templates/pydata/
last-updated.html``) to render "This page was last modified on <date>." as a
``<time>`` element. Its ``datetime`` attribute carries
``documenteer_last_modified_iso`` and its visible text is
``documenteer_last_modified_date`` (the UTC ``YYYY-MM-DD`` fallback);
``rubin-last-modified.js`` rewrites that text to the reader's local date.

The same datetime is also emitted into the page ``<head>`` as machine-readable
metadata -- ``article:modified_time`` (Open Graph), ``dcterms.modified``
(Dublin Core), and a Schema.org ``dateModified`` (JSON-LD) -- so that this
extension is the single source of truth for the page's last-modified date.

Using Git commit dates (rather than filesystem modification times) means the
timestamps are meaningful in CI builds, where checkouts have arbitrary mtimes.

.. important::

   The date is derived from the Git history, so CI checkouts must fetch the
   full history. With ``actions/checkout`` set ``fetch-depth: 0``; a shallow
   clone makes every page report the same (wrong) date.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import git
from sphinx.application import Sphinx
from sphinx.util import logging
from sphinx.util.i18n import format_date
from sphinx.util.typing import ExtensionMetadata

from ..conf._utils import GitRepository
from ..version import __version__

__all__ = ["LastModified", "setup"]

logger = logging.getLogger(__name__)


class LastModified:
    """Computes per-page "last modified" timestamps from Git commit history.

    A single instance is created in `setup`, which connects two
    ``html-page-context`` handlers:

    - `add_time_context` (early, before pydata-sphinx-theme's
      ``update_and_remove_templates``) exposes the UTC ``<time>`` context
      variables. pydata empty-checks the ``last-updated`` footer component and
      drops it unless these variables already exist when it runs, so they must
      be set first.
    - `add_last_modified` (late, after sphinx-last-updated-by-git's own
      handler) sets the human-readable ``last_updated`` value and appends the
      machine-readable ``<head>`` metadata.

    Both handlers share a single per-page Git computation via
    `get_last_modified_datetime`, which is memoized in ``_date_cache``.

    The instance lazily constructs a ``GitRepository`` on first use and
    remembers when timestamps can't be produced, so that those builds are a
    clean no-op. Timestamps are disabled when the source directory isn't a Git
    repository (including the pytest temporary source directory) and when the
    repository is a shallow clone (whose truncated history would yield
    misleading dates -- a warning is emitted in that case).
    """

    def __init__(self) -> None:
        self._repo: GitRepository | None = None
        # True once we've determined the srcdir isn't a usable Git repository,
        # so we don't retry (and re-log) on every page.
        self._disabled = False
        # Per-page memo of the computed last-modified datetime, so the two
        # html-page-context handlers don't each run the Git computation.
        self._date_cache: dict[str, datetime | None] = {}

    def _get_repository(self, app: Sphinx) -> GitRepository | None:
        """Get the cached ``GitRepository``, constructing it on first use.

        Returns `None` if the source directory isn't a Git repository.
        """
        if self._disabled:
            return None
        if self._repo is None:
            try:
                self._repo = GitRepository(Path(app.srcdir))
            except (git.InvalidGitRepositoryError, git.NoSuchPathError):
                self._disabled = True
                logger.debug(
                    "documenteer.ext.lastmodified: %s is not a Git "
                    "repository; skipping 'last updated' timestamps.",
                    app.srcdir,
                )
                return None
            if self._repo.is_shallow:
                # A shallow clone lacks the full history, so commit dates
                # collapse to the boundary commit's date. Rather than publish
                # misleading timestamps, disable the feature entirely (and warn
                # once) until the repository is fetched with full history.
                self._disabled = True
                self._repo = None
                logger.warning(
                    "documenteer.ext.lastmodified: the Git repository is a "
                    "shallow clone, so 'last updated' page timestamps would "
                    "be inaccurate and have been omitted. In CI, configure "
                    "actions/checkout with fetch-depth: 0 to fetch the full "
                    "history and enable them."
                )
                return None
        return self._repo

    def get_last_modified_datetime(
        self, app: Sphinx, pagename: str
    ) -> datetime | None:
        """Compute the most recent Git commit datetime for a page.

        Parameters
        ----------
        app
            The Sphinx application.
        pagename
            The docname of the page being rendered.

        Returns
        -------
        datetime.datetime or None
            The timezone-aware datetime of the most recent commit touching the
            page's own source file or any of its ``include``/``literalinclude``
            dependencies, or `None` if there's no Git repository or none of
            those files are tracked.
        """
        repo = self._get_repository(app)
        if repo is None:
            return None

        # The page's own source file (absolute path).
        source = Path(app.env.doc2path(pagename, base=True))

        # Files the page depends on (includes/literalinclude). Sphinx records
        # these as forward-slash paths that are either srcdir-relative or
        # absolute; the ``/`` operator handles both (an absolute dependency
        # replaces srcdir, mirroring os.path.join). compute_last_modified
        # resolves each path, so no explicit normalization is needed here.
        srcdir = Path(app.env.srcdir)
        dependencies = app.env.dependencies.get(pagename, set())
        paths: list[Path] = [source, *(srcdir / dep for dep in dependencies)]

        return repo.compute_last_modified(paths)

    def _resolve(
        self, app: Sphinx, pagename: str, doctree: object | None
    ) -> datetime | None:
        """Return the page's last-modified datetime, applying the gates once.

        Shared by both ``html-page-context`` handlers. The result is memoized
        per page so the (potentially expensive) Git computation runs only once
        even though two handlers consult it.

        Returns `None` -- so the caller emits nothing -- when the page has no
        source document, the feature is disabled, or no commit date is
        available.

        Parameters
        ----------
        app
            The Sphinx application.
        pagename
            The docname of the page being rendered.
        doctree
            The doctree for the page, or `None` for pages without a source
            document (such as ``genindex``, ``search``, and ``404``). These
            pages are skipped.
        """
        if doctree is None:
            # Pages such as genindex/search/404 have no source file.
            return None
        if not app.config.documenteer_last_modified_enabled:
            return None
        if pagename not in self._date_cache:
            self._date_cache[pagename] = self.get_last_modified_datetime(
                app, pagename
            )
        return self._date_cache[pagename]

    def add_time_context(
        self,
        app: Sphinx,
        pagename: str,
        templatename: str,
        context: dict,
        doctree: object | None,
    ) -> None:
        """Expose the UTC ``<time>`` context variables for the footer.

        This ``html-page-context`` handler runs *early* -- before
        pydata-sphinx-theme's ``update_and_remove_templates`` (priority 500),
        which empty-checks the ``last-updated`` footer component and drops it
        unless its context is already populated. Documenteer's override of that
        component renders a ``<time>`` element gated on
        ``documenteer_last_modified_iso``, so this handler must set it first:

        - ``documenteer_last_modified_iso`` -- the canonical UTC ISO 8601
          timestamp, used in the ``<time datetime="...">`` attribute (which
          ``rubin-last-modified.js`` localizes to the reader's timezone).
        - ``documenteer_last_modified_date`` -- the UTC date as ``YYYY-MM-DD``,
          the no-JavaScript visible fallback text.

        Parameters
        ----------
        app
            The Sphinx application.
        pagename
            The docname of the page being rendered.
        templatename
            The template used to render the page.
        context
            The template context, modified in place.
        doctree
            The doctree for the page, or `None` for pages without a source
            document (such pages are skipped).
        """
        date = self._resolve(app, pagename, doctree)
        if date is None:
            return

        utc_date = date.astimezone(UTC)
        context["documenteer_last_modified_iso"] = utc_date.isoformat()
        context["documenteer_last_modified_date"] = utc_date.strftime(
            "%Y-%m-%d"
        )

    def add_last_modified(
        self,
        app: Sphinx,
        pagename: str,
        templatename: str,
        context: dict,
        doctree: object | None,
    ) -> None:
        """Populate the ``last_updated`` value and ``<head>`` metadata.

        This ``html-page-context`` handler runs *late* -- after
        sphinx-last-updated-by-git's own handler (which the user-guide preset
        auto-loads through sphinx-sitemap and which resets ``last_updated`` to
        `None` when ``html_last_updated_fmt`` is unset) and after
        pydata-sphinx-theme's ``_fix_canonical_url`` (so the JSON-LD metadata
        sees the corrected ``pageurl``). It sets the ``last_updated`` context
        value -- formatted in the commit's own timezone offset and emitted by
        pydata-sphinx-theme as the ``docbuild:last-update`` meta tag -- and
        appends machine-readable last-modified metadata to the page ``<head>``.

        The ``<time>`` footer context variables are set separately and earlier
        by `add_time_context`.

        Parameters
        ----------
        app
            The Sphinx application.
        pagename
            The docname of the page being rendered.
        templatename
            The template used to render the page.
        context
            The template context, modified in place.
        doctree
            The doctree for the page, or `None` for pages without a source
            document (such pages are skipped).
        """
        date = self._resolve(app, pagename, doctree)
        if date is None:
            return

        fmt = app.config.documenteer_last_modified_date_format
        # Don't pass ``local_time``: it was only added to format_date() in
        # Sphinx 8 (where it defaults to False), and Sphinx 7 formats the date
        # as given. Relying on the default keeps output reproducible (the
        # commit datetime is used as-is, not converted to the builder's local
        # timezone) and compatible across both Sphinx versions.
        context["last_updated"] = format_date(
            fmt,
            date=date,
            language=app.config.language,
        )

        self._add_metadata(context, date.astimezone(UTC).isoformat())

    @staticmethod
    def _add_metadata(context: dict, iso: str) -> None:
        """Append machine-readable last-modified metadata to the page head.

        Emits the page's Git commit date through three complementary channels,
        all carrying the same ISO 8601 value, so that social-card scrapers,
        Dublin Core harvesters, and Schema.org/JSON-LD crawlers agree:

        - ``article:modified_time`` -- Open Graph.
        - ``dcterms.modified`` -- Dublin Core.
        - Schema.org ``dateModified`` on a ``WebPage`` -- JSON-LD. ``WebPage``
          keeps this a plain freshness statement without triggering the
          "missing field" validation noise that an ``Article`` would.

        The ISO value is normalized to UTC (``+00:00``) by the caller,
        independent of the committer's timezone offset, so these
        machine-readable freshness signals are byte-for-byte identical no
        matter who authored the commit (a local commit and its UTC-recorded
        squash-merge agree). This deliberately diverges from the
        human-readable ``last_updated`` footer date, which keeps the commit's
        own offset.

        Parameters
        ----------
        context
            The template context, modified in place. Its ``metatags`` string
            is extended with the new tags.
        iso
            The canonical UTC ISO 8601 last-modified timestamp.
        """
        metatags = context.get("metatags", "")

        metatags += (
            f'\n<meta property="article:modified_time" content="{iso}" />'
            f'\n<meta name="dcterms.modified" content="{iso}" />'
        )

        json_ld: dict[str, str] = {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "dateModified": iso,
        }
        # Guides set html_baseurl, so pageurl is usually available; tie the
        # statement to the page's canonical URL when it is.
        pageurl = context.get("pageurl")
        if pageurl:
            json_ld["@id"] = pageurl
            json_ld["url"] = pageurl
        # Escape ``<`` so a value can never terminate the <script> element
        # early (defense against early-script-termination injection).
        serialized = json.dumps(json_ld).replace("<", "\\u003c")
        metatags += (
            f'\n<script type="application/ld+json">{serialized}</script>'
        )

        context["metatags"] = metatags


def setup(app: Sphinx) -> ExtensionMetadata:
    """Set up the ``documenteer.ext.lastmodified`` Sphinx extension."""
    app.add_config_value(
        "documenteer_last_modified_enabled", True, "html", [bool]
    )
    app.add_config_value(
        "documenteer_last_modified_date_format", "%b %d, %Y", "html", [str]
    )

    # A single instance carries the cached Git repository and per-page date
    # memo across all pages in a build.
    last_modified = LastModified()

    # The two handlers bracket the default-priority (500) html-page-context
    # handlers of the themes/extensions we coexist with (lower numbers run
    # earlier):
    #
    # - add_time_context runs early (priority 400) so the
    #   documenteer_last_modified_iso/date context variables exist *before*
    #   pydata-sphinx-theme's update_and_remove_templates (priority 500)
    #   empty-checks the overridden last-updated footer component. Without
    #   this, that component renders empty and pydata drops it from the footer.
    # - add_last_modified runs late (priority 600) so it deterministically
    #   wins ``last_updated`` over sphinx_last_updated_by_git's priority-500
    #   handler (which resets it to None) and so the JSON-LD metadata sees the
    #   pageurl that pydata's _fix_canonical_url (priority 500) corrects.
    app.connect(
        "html-page-context", last_modified.add_time_context, priority=400
    )
    app.connect(
        "html-page-context", last_modified.add_last_modified, priority=600
    )

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
