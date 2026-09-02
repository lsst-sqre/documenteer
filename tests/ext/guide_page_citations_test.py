# type: ignore
"""Build tests for the per-page DOI landing-page metadata a user guide emits
for a ``[[project.citations]]`` entry that claims a page.

A site is the landing page of one DOI, but a site that publishes several works
can register a page of its own for each. An entry that sets ``page`` claims
that page: it, rather than every page of the site, carries the entry's DOI in
``citation_doi``, ``DC.identifier``, and the JSON-LD block. Every other page is
left exactly as it was.

These tests build the full user-guide stack because the head is where the
coupling between the configuration, ``documenteer.ext.citationpage``, and the
``layout.html`` override can be observed.
"""

from __future__ import annotations

import importlib.util
import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from lxml import html
from sphinx.testing.util import SphinxTestApp

# Must match the [[project.citations]] entries in
# tests/roots/test-guide-citationpage/documenteer.toml.
SELF_DOI = "10.71929/rubin/2570308"
BUTLER_DOI = "10.71929/rubin/3382539"
TAP_DOI = "10.71929/rubin/3382540"
VISIT_DOI = "10.71929/rubin/3382541"
MISSING_DOI = "10.71929/rubin/3382542"

# Must match project.base_url in that same file.
SITE_URL = "https://example.lsst.io"

# The citation JSON-LD block's own selector. The head carries a second
# application/ld+json block -- documenteer.ext.lastmodified's per-page WebPage
# freshness statement -- so the citation block is addressed by its id.
CITATION_JSONLD = '#documenteer-citation-metadata[type="application/ld+json"]'

# The missing-page warning's type.subtype, as ``suppress_warnings`` spells it
# and as Sphinx appends it to the rendered message.
WARNING_NAME = "documenteer.citation_page"

_HAS_PYDATA = importlib.util.find_spec("pydata_sphinx_theme") is not None

pytestmark = pytest.mark.skipif(
    not _HAS_PYDATA, reason="pydata_sphinx_theme is not installed"
)


def _mock_git_repository() -> MagicMock:
    """Build a mock GitRepository reporting a fixed commit date.

    The test root is copied to a throwaway srcdir that is not its own Git
    repository, so the real GitRepository would find no history.
    """
    mock_repo = MagicMock()
    mock_repo.is_shallow = False
    mock_repo.compute_last_modified.return_value = datetime(
        2024, 6, 1, tzinfo=UTC
    )
    return mock_repo


def _build(app: SphinxTestApp, pagename: str) -> html.HtmlElement:
    """Build the site and parse one of its pages."""
    with patch(
        "documenteer.ext.lastmodified.GitRepository",
        return_value=_mock_git_repository(),
    ):
        app.build()
    return html.fromstring(
        (app.outdir / f"{pagename}.html").read_text(encoding="utf-8")
    )


def _jsonld(doc: html.HtmlElement) -> dict:
    """Parse the page's citation JSON-LD block."""
    (script,) = doc.cssselect(f"head script{CITATION_JSONLD}")
    return json.loads(script.text_content())


@pytest.mark.sphinx(
    "html", testroot="guide-citationpage", srcdir="guide-citationpage"
)
def test_claimed_page_carries_its_own_doi(app: SphinxTestApp) -> None:
    """A page one entry claims emits that entry's DOI -- not the site's -- as
    its Highwire and Dublin Core meta tags, and describes it as the page's own
    subject with the page's URL.
    """
    doc = _build(app, "products/visit")

    (citation_doi,) = doc.cssselect('head meta[name="citation_doi"]')
    assert citation_doi.get("content") == VISIT_DOI
    (dc_identifier,) = doc.cssselect('head meta[name="DC.identifier"]')
    assert dc_identifier.get("content") == f"https://doi.org/{VISIT_DOI}"

    payload = _jsonld(doc)
    assert payload["@type"] == "Dataset"
    assert payload["@id"] == f"https://doi.org/{VISIT_DOI}"
    assert payload["name"] == "Visit table"
    # The claim names no fragment, so the whole page is the landing page.
    assert payload["url"] == f"{SITE_URL}/products/visit.html"


@pytest.mark.sphinx(
    "html", testroot="guide-citationpage", srcdir="guide-citationpage"
)
def test_claimed_page_still_displays_the_site_citation(
    app: SphinxTestApp,
) -> None:
    """A claim moves the page's machine-readable metadata and nothing else:
    the footer shows the same citations it shows everywhere, and an
    argument-less ``citation-card`` still means the site's own entry.
    """
    doc = _build(app, "products/visit")

    (footer,) = doc.cssselect(".rubin-footer__citation-text")
    assert f"https://doi.org/{SELF_DOI}" in footer.text_content()

    (card,) = doc.cssselect(".documenteer-citation-card__citation")
    assert f"https://doi.org/{SELF_DOI}" in card.text_content()


@pytest.mark.sphinx(
    "html", testroot="guide-citationpage", srcdir="guide-citationpage"
)
def test_doubly_claimed_page_emits_a_graph(app: SphinxTestApp) -> None:
    """A page two entries claim describes both as peers in a @graph, each at
    its own fragment, and emits no single-valued meta tag that would have to
    choose between them.
    """
    doc = _build(app, "products/object")

    assert not doc.cssselect('head meta[name="citation_doi"]')
    assert not doc.cssselect('head meta[name="DC.identifier"]')

    butler, tap = _jsonld(doc)["@graph"]
    assert butler["@id"] == f"https://doi.org/{BUTLER_DOI}"
    assert butler["url"] == f"{SITE_URL}/products/object.html#butler"
    assert tap["@id"] == f"https://doi.org/{TAP_DOI}"
    assert tap["url"] == f"{SITE_URL}/products/object.html#tap"


@pytest.mark.sphinx(
    "html", testroot="guide-citationpage", srcdir="guide-citationpage"
)
@pytest.mark.parametrize("pagename", ["index", "unclaimed"])
def test_unclaimed_page_keeps_the_site_citation(
    app: SphinxTestApp, pagename: str
) -> None:
    """A page no entry claims is untouched: it carries the site's own DOI and
    the site-wide JSON-LD block, with the page-claiming entries hanging off it
    as citations exactly as they did before ``page`` existed.
    """
    doc = _build(app, pagename)

    (citation_doi,) = doc.cssselect('head meta[name="citation_doi"]')
    assert citation_doi.get("content") == SELF_DOI

    payload = _jsonld(doc)
    assert payload["@id"] == f"https://doi.org/{SELF_DOI}"
    assert payload["url"] == f"{SITE_URL}/"
    assert [node["@id"] for node in payload["citation"]] == [
        f"https://doi.org/{BUTLER_DOI}",
        f"https://doi.org/{TAP_DOI}",
        f"https://doi.org/{VISIT_DOI}",
        f"https://doi.org/{MISSING_DOI}",
    ]


@pytest.mark.sphinx(
    "html", testroot="guide-citationpage", srcdir="guide-citationpage-missing"
)
def test_missing_page_warns(app: SphinxTestApp) -> None:
    """An entry claiming a docname the build does not contain warns, naming
    the docname, and the entry still works everywhere else.
    """
    doc = _build(app, "index")

    warnings = app.warning.getvalue()
    assert "products/missing" in warnings
    assert f"[{WARNING_NAME}]" in warnings, (
        "the warning must carry a type.subtype so that a -W build can "
        "suppress it by name"
    )
    # The entry is still one of the site's citations, so nothing else about
    # it is lost to the bad claim.
    assert f"https://doi.org/{MISSING_DOI}" in json.dumps(_jsonld(doc))


@pytest.mark.sphinx(
    "html",
    testroot="guide-citationpage",
    srcdir="guide-citationpage-suppressed",
    confoverrides={"suppress_warnings": [WARNING_NAME]},
)
def test_missing_page_warning_is_suppressible(app: SphinxTestApp) -> None:
    """The warning is suppressible by name, so a ``-W`` build that knowingly
    claims a page it has not written yet still passes.
    """
    _build(app, "index")

    assert "products/missing" not in app.warning.getvalue()


@pytest.mark.sphinx(
    "html",
    testroot="guide-citationpage",
    srcdir="guide-citationpage-nobaseurl",
    confoverrides={"html_baseurl": ""},
)
def test_claimed_page_without_a_base_url(app: SphinxTestApp) -> None:
    """A site that declares no base URL cannot know a page's own URL, so the
    claimed page's node keeps the doi.org redirect while still carrying the
    right DOI.
    """
    doc = _build(app, "products/visit")

    (citation_doi,) = doc.cssselect('head meta[name="citation_doi"]')
    assert citation_doi.get("content") == VISIT_DOI
    assert _jsonld(doc)["url"] == f"https://doi.org/{VISIT_DOI}"
