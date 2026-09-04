# type: ignore
"""Build tests for a user guide whose preferred citation is published
somewhere else.

``self`` and ``preferred`` answer two different questions. ``self`` says this
site is where a DOI resolves, and it alone drives the ``<head>`` metadata.
``preferred`` says which citation the site asks readers to use, and it alone
drives the visible surfaces — the argument-less ``citation-card`` and the
footer's default.

They coincide for a site that publishes its own DOI, and part ways for a
repository whose :file:`CITATION.cff` declares a ``preferred-citation``: that
paper is published elsewhere, so its landing page belongs to its publisher.
:file:`tests/roots/test-guide-preferred/documenteer.toml` is that site, built
here through the full user-guide stack because the rendered page is the only
place the split can be observed end to end.
"""

from __future__ import annotations

import importlib.util
import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from lxml import html
from sphinx.testing.util import SphinxTestApp

# Must match tests/roots/test-guide-preferred/documenteer.toml.
PAPER_DOI = "10.1117/12.2629569"
PAPER_DOI_URL = f"https://doi.org/{PAPER_DOI}"
PAPER_CITATION = (
    "Jenness, Tim (2022). The Vera C. Rubin Observatory Data Butler. "
    f"SPIE. {PAPER_DOI_URL}"
)
SITE_TITLE = "Preferred Citation Guide"
# Pydantic's HttpUrl gives the bare origin a trailing slash.
SITE_URL = "https://example.lsst.io/"
# The one work the site *is* the landing page of, on the page it claims.
DATASET_DOI = "10.71929/rubin/3382539"
DATASET_DOI_URL = f"https://doi.org/{DATASET_DOI}"
DATASET_TITLE = "Butler test dataset"

CARD = ".documenteer-citation-card"
CARD_LABEL = ".documenteer-citation-card__label"
CARD_CITATION = ".documenteer-citation-card__citation"
FOOTER_CITATION = ".rubin-footer__citation"
FOOTER_LABEL = ".rubin-footer__citation-label"
FOOTER_TEXT = ".rubin-footer__citation-text"
CITATION_JSONLD = '#documenteer-citation-metadata[type="application/ld+json"]'

_HAS_PYDATA = importlib.util.find_spec("pydata_sphinx_theme") is not None

pytestmark = pytest.mark.skipif(
    not _HAS_PYDATA, reason="pydata_sphinx_theme is not installed"
)


def _build(app: SphinxTestApp) -> html.HtmlElement:
    """Build the site and parse its index page.

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
    return _page(app, "index")


def _page(app: SphinxTestApp, pagename: str) -> html.HtmlElement:
    """Parse one page of a build that has already run."""
    return html.fromstring(
        (app.outdir / f"{pagename}.html").read_text(encoding="utf-8")
    )


def _jsonld(doc: html.HtmlElement) -> dict:
    """Parse a page's citation JSON-LD block."""
    (block,) = doc.cssselect(f"head script{CITATION_JSONLD}")
    return json.loads(block.text_content())


@pytest.mark.sphinx(
    "html", testroot="guide-preferred", srcdir="guide-preferred"
)
def test_preferred_citation_is_shown_without_a_self_entry(
    app: SphinxTestApp,
) -> None:
    """The argument-less card and the footer both render the preferred entry,
    so a site whose citation is published elsewhere still asks for it on
    every page.
    """
    doc = _build(app)

    (card,) = doc.cssselect(CARD)
    assert card.cssselect(CARD_LABEL)[0].text_content().strip() == "Paper"
    citation = " ".join(
        card.cssselect(CARD_CITATION)[0].text_content().split()
    )
    assert citation == PAPER_CITATION

    (footer,) = doc.cssselect(FOOTER_CITATION)
    assert footer.cssselect(FOOTER_LABEL)[0].text_content().strip() == "Paper"
    (link,) = footer.cssselect(f"{FOOTER_TEXT} a")
    assert link.get("href") == PAPER_DOI_URL

    assert "no citation is marked" not in app.warning.getvalue()


@pytest.mark.sphinx(
    "html", testroot="guide-preferred", srcdir="guide-preferred"
)
def test_head_claims_no_landing_page_without_a_self_entry(
    app: SphinxTestApp,
) -> None:
    """No page emits ``citation_doi`` or ``DC.identifier``.

    Those tags are the claim that this page is where the DOI resolves, and
    the paper resolves to SPIE. Emitting them here would tell a harvester the
    site is something it is not.
    """
    doc = _build(app)

    assert not doc.cssselect('head meta[name="citation_doi"]')
    assert not doc.cssselect('head meta[name="DC.identifier"]')


@pytest.mark.sphinx(
    "html", testroot="guide-preferred", srcdir="guide-preferred"
)
def test_jsonld_subject_is_the_site_without_a_self_entry(
    app: SphinxTestApp,
) -> None:
    """The JSON-LD block's subject is the site itself — a WebSite with the
    site's title and URL and no identifier — with the declared work under
    ``citation``.
    """
    payload = _jsonld(_build(app))

    assert payload["@type"] == "WebSite"
    assert payload["name"] == SITE_TITLE
    assert payload["url"] == SITE_URL
    assert "@id" not in payload
    assert "identifier" not in payload

    (paper,) = payload["citation"]
    assert paper["@type"] == "ScholarlyArticle"
    assert paper["@id"] == PAPER_DOI_URL
    assert paper["name"] == "The Vera C. Rubin Observatory Data Butler"


@pytest.mark.sphinx(
    "html", testroot="guide-preferred", srcdir="guide-preferred"
)
def test_claimed_page_relates_to_the_site_in_both_directions(
    app: SphinxTestApp,
) -> None:
    """A site that publishes no DOI of its own can still be the landing page
    of one, and the relation between that work and the site is stated at both
    ends: the site-wide block names the work under ``hasPart``, and the
    claimed page's own block names the site's ``WebSite`` node — which needs
    no DOI to be a target — under ``isPartOf``.
    """
    index = _build(app)
    dataset = _page(app, "dataset")

    assert _jsonld(index)["hasPart"] == [
        {
            "@type": "Dataset",
            "@id": DATASET_DOI_URL,
            "name": DATASET_TITLE,
        }
    ]

    payload = _jsonld(dataset)
    assert payload["@id"] == DATASET_DOI_URL
    assert payload["url"] == f"{SITE_URL}dataset.html"
    assert payload["isPartOf"] == {
        "@type": "WebSite",
        "name": SITE_TITLE,
        "url": SITE_URL,
    }
