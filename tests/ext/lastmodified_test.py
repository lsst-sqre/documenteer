# type: ignore
"""Tests for documenteer.ext.lastmodified."""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from sphinx.testing.util import SphinxTestApp

from documenteer.conf._utils import get_template_dir

FIXED_DATE = datetime(2024, 6, 1, tzinfo=UTC)
EXPECTED = "Jun 01, 2024"
# The ISO 8601 form of FIXED_DATE, as emitted into the page metadata.
EXPECTED_ISO = "2024-06-01T00:00:00+00:00"
# The UTC date as YYYY-MM-DD, the no-JavaScript visible footer fallback.
EXPECTED_DATE = "2024-06-01"

# A commit datetime in a non-UTC offset that also crosses a day boundary when
# normalized to UTC: 22:00 on Jun 01 at -07:00 is 05:00 on Jun 02 in UTC.
OFFSET_DATE = datetime(2024, 6, 1, 22, 0, tzinfo=timezone(timedelta(hours=-7)))
# The footer date keeps the commit's own offset (still Jun 01 locally).
OFFSET_EXPECTED = "Jun 01, 2024"
# The head metadata is normalized to UTC, shifting to the next day.
OFFSET_EXPECTED_ISO = "2024-06-02T05:00:00+00:00"

# Whether pydata-sphinx-theme is importable. The end-to-end render test must
# be skipped *before* the ``app`` fixture is built, because building with
# ``html_theme = "pydata_sphinx_theme"`` would otherwise error during fixture
# setup when the theme isn't installed.
_HAS_PYDATA = importlib.util.find_spec("pydata_sphinx_theme") is not None
# Whether sphinx-last-updated-by-git is importable. The user-guide preset
# auto-loads it through sphinx-sitemap; the guide-stack regression test loads
# it explicitly to reproduce the footer/last_updated interaction.
_HAS_GIT_EXT = (
    importlib.util.find_spec("sphinx_last_updated_by_git") is not None
)


def _mock_git_repository(date: datetime = FIXED_DATE) -> MagicMock:
    """Build a mock GitRepository that always reports a fixed commit date."""
    mock_repo = MagicMock()
    mock_repo.is_shallow = False
    mock_repo.compute_last_modified.return_value = date
    return mock_repo


def _build_and_capture(
    app: SphinxTestApp, mock_repo: MagicMock
) -> dict[str, dict]:
    """Build the app with GitRepository mocked, capturing each page's context.

    The probe handler is connected at a higher priority than the extension's
    handler (which runs at priority 600), so it observes the ``last_updated``
    value and ``metatags`` that the extension set (if any).
    """
    captured: dict[str, dict] = {}

    def probe(app, pagename, templatename, context, doctree):
        captured[pagename] = dict(context)

    app.connect("html-page-context", probe, priority=700)
    with patch(
        "documenteer.ext.lastmodified.GitRepository", return_value=mock_repo
    ):
        app.build()
    return captured


def _has_modified_metatags(context: dict) -> bool:
    """Whether a captured context carries any last-modified metadata.

    The extension only ever emits these tags together, so the Open Graph tag
    is a sufficient sentinel for the whole set.
    """
    return "article:modified_time" in context.get("metatags", "")


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
    "html", testroot="lastmodified", srcdir="lastmodified-timecontext"
)
def test_last_modified_time_context_vars(app: SphinxTestApp) -> None:
    """Content pages expose the UTC ISO and date context vars.

    These feed the ``<time>`` element rendered by the overridden
    ``last-updated`` component: the ISO value populates the ``datetime``
    attribute and the ``YYYY-MM-DD`` date is the no-JavaScript visible
    fallback.
    """
    mock_repo = _mock_git_repository()
    captured = _build_and_capture(app, mock_repo)

    assert captured["index"]["documenteer_last_modified_iso"] == EXPECTED_ISO
    assert captured["index"]["documenteer_last_modified_date"] == EXPECTED_DATE


@pytest.mark.sphinx(
    "html", testroot="lastmodified", srcdir="lastmodified-metatags"
)
def test_last_modified_metatags_on_content_pages(app: SphinxTestApp) -> None:
    """Content pages emit Open Graph, Dublin Core, and JSON-LD metadata.

    All three signals carry the same ISO 8601 Git commit date, making the
    extension the single source of truth for the page's last-modified date.
    """
    mock_repo = _mock_git_repository()
    captured = _build_and_capture(app, mock_repo)

    metatags = captured["index"]["metatags"]
    assert (
        f'<meta property="article:modified_time" content="{EXPECTED_ISO}" />'
        in metatags
    )
    assert (
        f'<meta name="dcterms.modified" content="{EXPECTED_ISO}" />'
        in metatags
    )
    assert '<script type="application/ld+json">' in metatags
    assert f'"dateModified": "{EXPECTED_ISO}"' in metatags


@pytest.mark.sphinx(
    "html", testroot="lastmodified", srcdir="lastmodified-metatags-utc"
)
def test_last_modified_metatags_utc_normalized(app: SphinxTestApp) -> None:
    """Head metadata is normalized to UTC; the footer keeps the commit offset.

    A commit recorded at a non-UTC offset (here ``-07:00``) is emitted into the
    HTML ``<head>`` as a UTC (``+00:00``) ISO 8601 string, so the machine
    signals are contributor-independent. Because this commit's local time is
    late in the day, the UTC value rolls over to the next day -- yet the
    human-readable footer date stays on the commit's own (earlier) day.
    """
    mock_repo = _mock_git_repository(OFFSET_DATE)
    captured = _build_and_capture(app, mock_repo)

    metatags = captured["index"]["metatags"]
    assert (
        f'<meta property="article:modified_time" '
        f'content="{OFFSET_EXPECTED_ISO}" />' in metatags
    )
    assert (
        f'<meta name="dcterms.modified" content="{OFFSET_EXPECTED_ISO}" />'
        in metatags
    )
    assert f'"dateModified": "{OFFSET_EXPECTED_ISO}"' in metatags

    # The visible footer date keeps the commit's own offset (the head-only
    # scope of the UTC normalization).
    assert captured["index"]["last_updated"] == OFFSET_EXPECTED

    # The <time> context vars track UTC, so they roll over to the next day
    # while ``last_updated`` stays on the commit's earlier day.
    assert (
        captured["index"]["documenteer_last_modified_iso"]
        == OFFSET_EXPECTED_ISO
    )
    assert captured["index"]["documenteer_last_modified_date"] == "2024-06-02"


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

    # Sourceless pages also get no last-modified metadata.
    assert not _has_modified_metatags(captured["genindex"])
    assert not _has_modified_metatags(captured["search"])


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

    # No last-modified metadata is emitted when the feature is disabled.
    assert not _has_modified_metatags(captured["index"])
    assert not _has_modified_metatags(captured["page2"])


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

    # Misleading metadata is suppressed along with the visible timestamp.
    assert not _has_modified_metatags(captured["index"])
    assert not _has_modified_metatags(captured["page2"])

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
        "html_theme_options": {"article_footer_items": ["last-updated"]},
        "templates_path": [get_template_dir("pydata")],
    },
)
def test_last_updated_rendered_in_pydata_article(app: SphinxTestApp) -> None:
    """End-to-end: the date appears at the bottom of the rendered article.

    Documenteer's pydata templates are added to the build so the overriding
    ``last-updated.html`` component (which renders the ``<time>`` element) is
    exercised.
    """
    mock_repo = _mock_git_repository()
    with patch(
        "documenteer.ext.lastmodified.GitRepository", return_value=mock_repo
    ):
        app.build()

    html = (app.outdir / "index.html").read_text()
    # The overriding component renders the page-level wording and the <time>
    # element: the UTC ISO in the datetime attribute and the YYYY-MM-DD UTC
    # fallback as the visible text.
    assert "This page was last modified on" in html
    assert f'<time datetime="{EXPECTED_ISO}"' in html
    assert f">{EXPECTED_DATE}</time>" in html
    # The machine-readable Open Graph tag is rendered into the page <head>.
    assert (
        f'<meta property="article:modified_time" content="{EXPECTED_ISO}" />'
        in html
    )


@pytest.mark.skipif(
    not (_HAS_PYDATA and _HAS_GIT_EXT),
    reason="pydata_sphinx_theme and sphinx_last_updated_by_git are required",
)
@pytest.mark.sphinx(
    "html",
    testroot="lastmodified",
    srcdir="lastmodified-guidestack",
    confoverrides={
        "extensions": [
            "sphinx_last_updated_by_git",
            "documenteer.ext.lastmodified",
        ],
        "html_theme": "pydata_sphinx_theme",
        "html_theme_options": {"article_footer_items": ["last-updated"]},
        "templates_path": [get_template_dir("pydata")],
        # Mirror the user-guide preset, which silences git-ext's duplicate tag.
        "git_last_updated_metatags": False,
    },
)
def test_last_updated_rendered_with_git_extension(app: SphinxTestApp) -> None:
    """End-to-end with sphinx-last-updated-by-git loaded, as in the guide.

    The guide preset auto-loads sphinx-last-updated-by-git (through
    sphinx-sitemap). Its html-page-context handler resets ``last_updated`` to
    `None` (``html_last_updated_fmt`` is unset). This regression test pins the
    handler priority bracketing: the ``<time>`` footer component still survives
    pydata's empty-check (so the footer renders) and the late handler still
    restores ``last_updated`` (so the ``docbuild:last-update`` tag is emitted).
    """
    mock_repo = _mock_git_repository()
    with patch(
        "documenteer.ext.lastmodified.GitRepository", return_value=mock_repo
    ):
        app.build()

    html = (app.outdir / "index.html").read_text()
    # The footer component renders despite git-ext clearing last_updated.
    assert "This page was last modified on" in html
    assert f'<time datetime="{EXPECTED_ISO}"' in html
    # The late handler wins last_updated, so pydata's meta tag carries it.
    assert f'<meta name="docbuild:last-update" content="{EXPECTED}"' in html
    # Documenteer remains the single source of the Open Graph tag (git-ext's
    # duplicate is silenced).
    assert (
        f'<meta property="article:modified_time" content="{EXPECTED_ISO}" />'
        in html
    )
    assert html.count('property="article:modified_time"') == 1
