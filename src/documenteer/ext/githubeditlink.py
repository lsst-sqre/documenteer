"""Sphinx extension that resolves the in-repository path used by the "Edit on
GitHub" button.

pydata-sphinx-theme builds the edit URL as::

    {github_url}/{github_user}/{github_repo}/edit/{github_version}/{doc_path}{file_name}

where ``file_name`` is the page's docname plus its source suffix — a path
relative to the Sphinx **source** directory. ``doc_path`` must therefore be the
*source* directory's path within the Git working tree.

That value cannot be computed in :file:`conf.py`, which is where the rest of
the "Edit on GitHub" context is set. At ``conf.py`` exec time there is no
Sphinx application and hence no ``srcdir``; the only path available is the
current working directory, which Sphinx sets to the directory containing
``conf.py`` (the *config* directory). Those two directories are the same in
many projects, but not all: ``sphinx-build -c . docs _build/html`` puts the
config directory at the repository root and the source directory in
:file:`docs/`. Deriving ``doc_path`` from the config directory there yields a
plausible-looking URL that 404s.

This extension therefore computes ``doc_path`` from ``app.srcdir`` at
``config-inited``, the earliest event where the source directory is known.
``config-inited`` (rather than ``builder-inited``) is also the last event at
which the button can still be turned off, because ``builder.init()`` — which
resolves ``html_theme_options`` into the theme — runs *before*
``builder-inited`` is emitted.

Ordering against pydata-sphinx-theme needs no special handling: that theme
connects its own handlers to ``builder-inited`` and ``html-page-context``, and
does nothing at ``config-inited``.

Outside a Git checkout (an sdist, a vendored documentation tree, a Docker image
built without :file:`.git`) the path can't be determined, so the button is
silently omitted rather than rendered with a wrong path.
"""

from __future__ import annotations

from pathlib import Path

import git
from sphinx.application import Sphinx
from sphinx.config import Config
from sphinx.util import logging
from sphinx.util.typing import ExtensionMetadata

from ..conf._utils import GitRepository
from ..version import __version__

__all__ = ["set_doc_path", "setup"]

logger = logging.getLogger(__name__)


def _disable_edit_button(config: Config) -> None:
    """Suppress the "Edit on GitHub" button for this build.

    Turning off ``use_edit_page_button`` is sufficient: pydata-sphinx-theme's
    ``edit-this-page`` component is gated on the resulting
    ``theme_use_edit_page_button`` template variable, so the theme never tries
    to build an edit URL (and never raises for the missing context).
    """
    config.html_theme_options["use_edit_page_button"] = False
    # Drop any stale value so a leftover path can't leak into the context.
    config.html_context.pop("doc_path", None)


def set_doc_path(app: Sphinx, config: Config) -> None:
    """Set ``html_context["doc_path"]`` from the source directory's location
    in the Git working tree.

    Parameters
    ----------
    app
        The Sphinx application. Its ``srcdir`` is already resolved by Sphinx.
    config
        The Sphinx configuration, modified in place.
    """
    if not config.html_theme_options.get("use_edit_page_button"):
        # Presets that don't use the edit button (such as the technote preset)
        # leave this extension inert.
        return

    try:
        repo = GitRepository(Path(app.srcdir))
    except (git.InvalidGitRepositoryError, git.NoSuchPathError):
        # Deliberately info, not warning: Rubin projects build with ``-W``, and
        # building outside a Git checkout is legitimate, so a warning would
        # turn a cosmetic degradation into a build failure. (This also diverges
        # from documenteer.ext.lastmodified, which logs at debug; this message
        # explains a *missing* UI element, so it's worth showing by default.)
        logger.info(
            "documenteer.ext.githubeditlink: %s is not in a Git repository; "
            "omitting the 'Edit on GitHub' button.",
            app.srcdir,
        )
        _disable_edit_button(config)
        return

    doc_path = repo.compute_relative_path(app.srcdir)
    if doc_path is None:
        # A repository was found from the source directory, yet the source
        # directory isn't inside its working tree. Both paths are resolved, so
        # this shouldn't be reachable in a normal checkout; warn because it
        # signals a genuinely odd setup (a bind mount, say) rather than the
        # expected non-Git case.
        logger.warning(
            "documenteer.ext.githubeditlink: could not determine the path of "
            "%s relative to the Git working tree at %s; omitting the 'Edit on "
            "GitHub' button.",
            app.srcdir,
            repo.working_tree_dir,
        )
        _disable_edit_button(config)
        return

    config.html_context["doc_path"] = doc_path


def setup(app: Sphinx) -> ExtensionMetadata:
    """Set up the ``documenteer.ext.githubeditlink`` Sphinx extension."""
    app.connect("config-inited", set_doc_path)

    return {
        "version": __version__,
        # The handler runs once, at config-inited, in the main process.
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
