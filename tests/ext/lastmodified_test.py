# type: ignore
"""Tests for documenteer.ext.lastmodified."""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from sphinx.testing.util import SphinxTestApp

FIXED_DATE = datetime(2024, 6, 1, tzinfo=UTC)
EXPECTED = "Jun 01, 2024"

# Whether pydata-sphinx-theme is importable. The end-to-end footer test must
# be skipped *before* the ``app`` fixture is built, because building with
# ``html_theme = "pydata_sphinx_theme"`` would otherwise error during fixture
# setup when the theme isn't installed.
_HAS_PYDATA = importlib.util.find_spec("pydata_sphinx_theme") is not None


def _mock_git_repository() -> MagicMock:
    """Build a mock GitRepository that always reports a fixed commit date."""
    mock_repo = MagicMock()
    mock_repo.is_shallow = False
    mock_repo.compute_last_modified.return_value = FIXED_DATE
    return mock_repo


def _build_and_capture(
    app: SphinxTestApp, mock_repo: MagicMock
) -> dict[str, dict]:
    """Build the app with GitRepository mocked, capturing each page's context.

    The probe handler is connected after the extension's handler, so it
    observes the ``last_updated`` value that the extension set (if any).
    """
    captured: dict[str, dict] = {}

    def probe(app, pagename, templatename, context, doctree):
        captured[pagename] = dict(context)

    app.connect("html-page-context", probe)
    with patch(
        "documenteer.ext.lastmodified.GitRepository", return_value=mock_repo
    ):
        app.build()
    return captured


@pytest.mark.sphinx(
    "html", testroot="lastmodified", srcdir="lastmodified-content"
)
def test_last_updated_on_content_pages(app: SphinxTestApp) -> None:
    """Content pages get a formatted ``last_updated`` context value."""
    mock_repo = _mock_git_repository()
    captured = _build_and_capture(app, mock_repo)

    assert captured["index"]["last_updated"] == EXPECTED
    assert captured["page2"]["last_updated"] == EXPECTED

    # The included snippet is among the paths considered for the index page,
    # demonstrating that include/literalinclude dependencies are accounted for.
    considered = [
        str(path)
        for call in mock_repo.compute_last_modified.call_args_list
        for path in call.args[0]
    ]
    assert any(path.endswith("snippet.txt") for path in considered)


@pytest.mark.sphinx(
    "html", testroot="lastmodified", srcdir="lastmodified-special"
)
def test_last_updated_none_on_special_pages(app: SphinxTestApp) -> None:
    """genindex/search pages (no source doctree) keep ``last_updated`` falsy.

    Sphinx always seeds ``last_updated`` in the global context (as ``None``
    when ``html_last_updated_fmt`` is unset). The extension leaves that value
    untouched for sourceless pages, so the footer component (which renders
    only when the value is truthy) stays hidden there.
    """
    mock_repo = _mock_git_repository()
    captured = _build_and_capture(app, mock_repo)

    assert captured["genindex"]["last_updated"] is None
    assert captured["search"]["last_updated"] is None


@pytest.mark.sphinx(
    "html",
    testroot="lastmodified",
    srcdir="lastmodified-disabled",
    confoverrides={"documenteer_last_modified_enabled": False},
)
def test_last_updated_disabled(app: SphinxTestApp) -> None:
    """When disabled, no page gets a date and Git is not consulted.

    The ``last_updated`` key remains at Sphinx's default of ``None`` because
    the extension returns early before consulting Git.
    """
    mock_repo = _mock_git_repository()
    captured = _build_and_capture(app, mock_repo)

    assert captured["index"]["last_updated"] is None
    assert captured["page2"]["last_updated"] is None
    mock_repo.compute_last_modified.assert_not_called()


@pytest.mark.sphinx(
    "html", testroot="lastmodified", srcdir="lastmodified-shallow"
)
def test_last_updated_suppressed_for_shallow_clone(app: SphinxTestApp) -> None:
    """A shallow clone suppresses dates entirely and warns once.

    Showing the boundary commit's date for every page would publish
    misleading data, so the extension omits the timestamp instead.
    """
    mock_repo = _mock_git_repository()
    mock_repo.is_shallow = True
    captured = _build_and_capture(app, mock_repo)

    # No page gets a date, and Git is never consulted for commit history.
    assert captured["index"]["last_updated"] is None
    assert captured["page2"]["last_updated"] is None
    mock_repo.compute_last_modified.assert_not_called()

    # The user is warned exactly once about the shallow clone.
    warnings = app.warning.getvalue()
    assert warnings.count("shallow clone") == 1
    assert "fetch-depth: 0" in warnings


@pytest.mark.skipif(
    not _HAS_PYDATA, reason="pydata_sphinx_theme is not installed"
)
@pytest.mark.sphinx(
    "html",
    testroot="lastmodified",
    srcdir="lastmodified-pydata",
    confoverrides={
        "html_theme": "pydata_sphinx_theme",
        "html_theme_options": {"footer_center": ["last-updated"]},
    },
)
def test_last_updated_rendered_in_pydata_footer(app: SphinxTestApp) -> None:
    """End-to-end: the date appears in the rendered pydata footer."""
    mock_repo = _mock_git_repository()
    with patch(
        "documenteer.ext.lastmodified.GitRepository", return_value=mock_repo
    ):
        app.build()

    html = (app.outdir / "index.html").read_text()
    assert EXPECTED in html
