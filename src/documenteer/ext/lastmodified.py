"""Sphinx extension that adds a "Last updated" timestamp to each page based
on the page's Git commit history.

For each HTML output page, this extension computes the most recent commit
datetime across the page's source file *and* any files that the page pulls in
via ``include``/``literalinclude`` directives. That datetime is formatted and
stored in the page's ``last_updated`` template context variable, which the
pydata-sphinx-theme renders in its ``last-updated`` footer component.

Using Git commit dates (rather than filesystem modification times) means the
timestamps are meaningful in CI builds, where checkouts have arbitrary mtimes.

.. important::

   The date is derived from the Git history, so CI checkouts must fetch the
   full history. With ``actions/checkout`` set ``fetch-depth: 0``; a shallow
   clone makes every page report the same (wrong) date.
"""

from __future__ import annotations

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

    def get_last_modified(self, app: Sphinx, pagename: str) -> str | None:
        """Compute the formatted "last updated" date for a page.

        Parameters
        ----------
        app
            The Sphinx application.
        pagename
            The docname of the page being rendered.

        Returns
        -------
        str or None
            The formatted date, or `None` if there's no Git repository or none
            of the page's source/dependency files are tracked.
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

        date = repo.compute_last_modified(paths)
        if date is None:
            return None

        fmt = app.config.documenteer_last_modified_date_format
        # Don't pass ``local_time``: it was only added to format_date() in
        # Sphinx 8 (where it defaults to False), and Sphinx 7 formats the date
        # as given. Relying on the default keeps output reproducible (the
        # commit datetime is used as-is, not converted to the builder's local
        # timezone) and compatible across both Sphinx versions.
        return format_date(
            fmt,
            date=date,
            language=app.config.language,
        )

    def add_last_modified(
        self,
        app: Sphinx,
        pagename: str,
        templatename: str,
        context: dict,
        doctree: object | None,
    ) -> None:
        """Populate the ``last_updated`` template context for a page.

        This is the ``html-page-context`` event handler. It runs once per
        output page, immediately before the page is rendered.

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

        formatted = self.get_last_modified(app, pagename)
        if formatted is not None:
            context["last_updated"] = formatted


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
    app.connect("html-page-context", last_modified.add_last_modified)

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
