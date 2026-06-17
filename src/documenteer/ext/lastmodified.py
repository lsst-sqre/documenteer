"""Sphinx extension that adds a "Last updated" timestamp to each page based
on the page's Git commit history.

For each HTML output page, this extension computes the most recent commit
datetime across the page's source file *and* any files that the page pulls in
via ``include``/``literalinclude`` directives. That datetime is formatted and
stored in the page's ``last_updated`` template context variable, which the
pydata-sphinx-theme renders at the bottom of the article body via its
``last-updated`` component.

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

    A single instance is created in `setup` and its
    `add_last_modified` method is connected to the ``html-page-context``
    event. The instance lazily constructs a ``GitRepository`` on first use and
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

    def add_last_modified(
        self,
        app: Sphinx,
        pagename: str,
        templatename: str,
        context: dict,
        doctree: object | None,
    ) -> None:
        """Populate the last-modified context and metadata for a page.

        This is the ``html-page-context`` event handler. It runs once per
        output page, immediately before the page is rendered. It sets the
        ``last_updated`` context value (rendered in the article footer and
        emitted by pydata-sphinx-theme as the ``docbuild:last-update`` meta
        tag) and appends machine-readable last-modified metadata to the page's
        ``<head>``.

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
            document (such as ``genindex``, ``search``, and ``404``). These
            pages are skipped.
        """
        if doctree is None:
            # Pages such as genindex/search/404 have no source file.
            return

        if not app.config.documenteer_last_modified_enabled:
            return

        date = self.get_last_modified_datetime(app, pagename)
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

        self._add_metadata(context, date)

    @staticmethod
    def _add_metadata(context: dict, date: datetime) -> None:
        """Append machine-readable last-modified metadata to the page head.

        Emits the page's Git commit date through three complementary channels,
        all carrying the same ISO 8601 value, so that social-card scrapers,
        Dublin Core harvesters, and Schema.org/JSON-LD crawlers agree:

        - ``article:modified_time`` -- Open Graph.
        - ``dcterms.modified`` -- Dublin Core.
        - Schema.org ``dateModified`` on a ``WebPage`` -- JSON-LD. ``WebPage``
          keeps this a plain freshness statement without triggering the
          "missing field" validation noise that an ``Article`` would.

        The ISO value is normalized to UTC (``+00:00``), independent of the
        committer's timezone offset, so these machine-readable freshness
        signals are byte-for-byte identical no matter who authored the commit
        (a local commit and its UTC-recorded squash-merge agree). This
        deliberately diverges from the human-readable footer date, which keeps
        the commit's own offset.

        Parameters
        ----------
        context
            The template context, modified in place. Its ``metatags`` string
            is extended with the new tags.
        date
            The timezone-aware last-modified datetime.
        """
        # Normalize to UTC so the machine-readable metadata is canonical and
        # contributor-independent, not tied to the committer's local offset.
        iso = date.astimezone(UTC).isoformat()
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

    # A single instance carries the cached Git repository across all pages in
    # a build.
    last_modified = LastModified()
    # Connect with an explicit later priority (the default is 500; higher
    # numbers run later) so this handler deterministically wins over
    # sphinx_last_updated_by_git's html-page-context handler -- which also
    # writes ``last_updated`` -- regardless of the order the extensions appear
    # in the extensions list. The last writer wins, and we want it to be us.
    app.connect(
        "html-page-context", last_modified.add_last_modified, priority=600
    )

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
