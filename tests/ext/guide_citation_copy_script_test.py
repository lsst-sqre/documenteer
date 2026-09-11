# type: ignore
"""Build tests for the pages a user guide references ``rubin-citation-copy.js``
from.

The script wires up the ``Copy BibTeX`` button both citation surfaces carry --
the site footer's and the ``citation-card`` directive's -- and removes it where
the clipboard API is unavailable. ``documenteer.ext.citationcard`` references
it per page, from the pages that carry such a button and no others; the guide
preset's part is only to copy the file into ``_static/``.

Per-page is what an API-heavy guide needs. A package site that shows its
citation on one card and keeps it out of the footer has one page with a button
and several hundred without, and referencing the script site-wide would load it
on all of them. These tests build four sites -- a footer-showing one, that
card-only shape, one that declares a citation and displays it nowhere, and one
that declares none -- because the referenced scripts of a rendered page are the
only place the coupling can be observed.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from lxml import html
from sphinx.testing.util import SphinxTestApp

# The script every citation surface's copy button needs.
COPY_SCRIPT = "rubin-citation-copy.js"

_HAS_PYDATA = importlib.util.find_spec("pydata_sphinx_theme") is not None

pytestmark = pytest.mark.skipif(
    not _HAS_PYDATA, reason="pydata_sphinx_theme is not installed"
)


def _build(app: SphinxTestApp) -> None:
    """Build the site.

    The test root is copied to a throwaway srcdir that is not its own Git
    repository, so ``documenteer.ext.lastmodified``'s repository is mocked to
    report a fixed commit date rather than failing to find any history.
    """
    mock_repo = MagicMock()
    mock_repo.is_shallow = False
    mock_repo.compute_last_modified.return_value = datetime(
        2024, 6, 1, tzinfo=UTC
    )
    with patch(
        "documenteer.ext.lastmodified.GitRepository", return_value=mock_repo
    ):
        app.build()


def _references_script(app: SphinxTestApp, page: str) -> bool:
    """Report whether one built page references the copy script.

    Sphinx appends a cache-busting ``?v=`` query to every script's ``src``, so
    the reference is matched on its path rather than compared whole.
    """
    doc = html.fromstring((app.outdir / page).read_text(encoding="utf-8"))
    return any(
        f"_static/{COPY_SCRIPT}" in (script.get("src") or "")
        for script in doc.cssselect("script")
    )


@pytest.mark.sphinx("html", testroot="guide", srcdir="guide-copy-footer")
def test_footer_site_references_the_script_everywhere(
    app: SphinxTestApp,
) -> None:
    """A site whose footer shows a citation references the script on every
    page, including the pages Sphinx generates without a source document.

    The footer is on all of them, so a button is on all of them -- ``genindex``
    and ``search`` included, which is why the footer answer cannot be a
    question about the page's doctree.
    """
    _build(app)

    assert (app.outdir / "_static" / COPY_SCRIPT).is_file()
    for page in ("index.html", "hidden.html", "genindex.html", "search.html"):
        assert _references_script(app, page), f"{page} carries a footer button"


@pytest.mark.sphinx(
    "html", testroot="guide-cardonly", srcdir="guide-copy-cardonly"
)
def test_card_only_site_references_the_script_on_the_card_page(
    app: SphinxTestApp,
) -> None:
    """A site that keeps its citation out of the footer and shows it on one
    card references the script on that page alone.

    This is the shape an API-heavy guide adopts, where the page with the card
    is one of hundreds; the rest have no button to wire and load no script.
    """
    _build(app)

    assert (app.outdir / "_static" / COPY_SCRIPT).is_file()
    assert _references_script(app, "index.html")
    assert not _references_script(app, "api.html")
    assert not _references_script(app, "genindex.html")


@pytest.mark.sphinx(
    "html", testroot="guide-undisplayed", srcdir="guide-copy-undisplayed"
)
def test_undisplayed_citation_references_no_script(
    app: SphinxTestApp,
) -> None:
    """A site that declares a citation and displays it nowhere references the
    script on no page.

    Declaring a citation is not displaying one: with nothing preferred, no
    ``self``, no entry in the footer, and no card, the site has no copy button
    anywhere, so no page loads the script that wires one.
    """
    _build(app)

    assert not _references_script(app, "index.html")
    assert not _references_script(app, "genindex.html")


@pytest.mark.sphinx(
    "html", testroot="guide-nocitations", srcdir="guide-copy-nocitations"
)
def test_site_without_citations_ships_no_script(app: SphinxTestApp) -> None:
    """A guide with no citations has nothing to copy, so it neither ships the
    script nor references it.
    """
    _build(app)

    assert not (app.outdir / "_static" / COPY_SCRIPT).exists()
    assert not _references_script(app, "index.html")


@pytest.mark.sphinx(
    "html", testroot="guide-cardonly", srcdir="guide-copy-rebuild"
)
def test_rebuild_that_adds_a_card_adds_the_script(
    app: SphinxTestApp, make_app: Callable[..., SphinxTestApp]
) -> None:
    """Adding a card to a page of an already-built site references the script
    on that page.

    The page's own resolved doctree is what the reference is decided from, and
    Sphinx hands each written page its own, so an incremental build that
    rewrites one page reaches the same answer a full build does. Nothing is
    remembered between builds, which is what a check reading the build
    environment would have to get right.
    """
    _build(app)
    assert not _references_script(app, "api.html")

    source = Path(app.srcdir) / "api.rst"
    source.write_text(
        f"{source.read_text(encoding='utf-8')}\n.. citation-card::\n",
        encoding="utf-8",
    )
    rebuilt = make_app("html", srcdir=app.srcdir)
    _build(rebuilt)

    assert _references_script(rebuilt, "api.html")
    assert _references_script(rebuilt, "index.html")
