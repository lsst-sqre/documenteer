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
# The visit entry's title carries the characters that would break out of a
# meta tag or a script element, so every escaping path is exercised.
VISIT_TITLE = 'Visit "raw" <all> table'
MISSING_DOI = "10.71929/rubin/3382542"
# A work the site cites rather than publishes, shown in the footer.
PAPER_DOI = "10.5281/zenodo.10385501"
# A work the site neither publishes nor shows anywhere site-wide.
UNLISTED_DOI = "10.5281/zenodo.10385502"

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


def _meta(doc: html.HtmlElement) -> dict[str, str]:
    """Read the page's citation meta tags, keyed by name."""
    return {
        element.get("name"): element.get("content")
        for element in doc.cssselect("head meta[name]")
        if element.get("name").startswith(("citation_", "DC."))
    }


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
    assert payload["name"] == VISIT_TITLE
    # The claim names no fragment, so the whole page is the landing page.
    assert payload["url"] == f"{SITE_URL}/products/visit.html"


@pytest.mark.sphinx(
    "html", testroot="guide-citationpage", srcdir="guide-citationpage"
)
def test_claimed_page_carries_the_claiming_entrys_highwire_set(
    app: SphinxTestApp,
) -> None:
    """The whole Highwire set on a claimed page describes the claiming entry,
    at the page's own URL rather than the site's, and its title reaches the
    ``content`` attribute escaped -- the quotes and angle brackets in it would
    otherwise close the attribute and open elements of their own.
    """
    doc = _build(app, "products/visit")

    assert _meta(doc) == {
        "citation_title": VISIT_TITLE,
        "citation_author": "Vera C. Rubin Observatory",
        "citation_publication_date": "2025/06/30",
        "citation_doi": VISIT_DOI,
        "citation_publisher": "Vera C. Rubin Observatory",
        "citation_fulltext_html_url": f"{SITE_URL}/products/visit.html",
        "DC.identifier": f"https://doi.org/{VISIT_DOI}",
    }

    # The parsed attribute above proves the title survived; this proves it was
    # written as entities rather than as raw markup the parser recovered from.
    raw = (app.outdir / "products/visit.html").read_text(encoding="utf-8")
    assert (
        '<meta name="citation_title" content="Visit &quot;raw&quot; '
        '&lt;all&gt; table">' in raw
    )


@pytest.mark.sphinx(
    "html", testroot="guide-citationpage", srcdir="guide-citationpage"
)
def test_claimed_page_is_part_of_the_site(app: SphinxTestApp) -> None:
    """The work a page is the landing page of is a part of the release the
    site as a whole is, so the page's node points back at the site's citation
    by reference -- the other half of the ``hasPart`` relation the site-wide
    block states.
    """
    doc = _build(app, "products/visit")

    assert _jsonld(doc)["isPartOf"] == {
        "@type": "Dataset",
        "@id": f"https://doi.org/{SELF_DOI}",
        "name": "Citation Page Test Release",
    }


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

    footer, _ = doc.cssselect(".rubin-footer__citation-text")
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

    # The whole set is single-valued, so none of it is emitted rather than
    # the site's own tags being left in place to misdescribe the page.
    assert _meta(doc) == {}

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
    the site-wide JSON-LD block, in which each entry appears as the relation
    it has to the site rather than as a record repeated in full.
    """
    doc = _build(app, pagename)

    (citation_doi,) = doc.cssselect('head meta[name="citation_doi"]')
    assert citation_doi.get("content") == SELF_DOI

    payload = _jsonld(doc)
    assert payload["@id"] == f"https://doi.org/{SELF_DOI}"
    assert payload["url"] == f"{SITE_URL}/"

    # Every entry that claims a page is a part of the release, named by
    # reference because its own landing page carries the full record.
    assert payload["hasPart"] == [
        {
            "@type": "Dataset",
            "@id": f"https://doi.org/{BUTLER_DOI}",
            "name": "Object catalog (Butler)",
        },
        {
            "@type": "Dataset",
            "@id": f"https://doi.org/{TAP_DOI}",
            "name": "Object catalog (TAP)",
        },
        {
            "@type": "Dataset",
            "@id": f"https://doi.org/{VISIT_DOI}",
            "name": VISIT_TITLE,
        },
        {
            "@type": "Dataset",
            "@id": f"https://doi.org/{MISSING_DOI}",
            "name": "Retired catalog",
        },
    ]

    # The footer's paper is a work the site cites, and no page of the site
    # describes it, so it appears in full.
    (paper,) = payload["citation"]
    assert paper["@id"] == f"https://doi.org/{PAPER_DOI}"
    assert paper["@type"] == "ScholarlyArticle"
    assert paper["creator"] == [
        {
            "@type": "Person",
            "@id": "https://orcid.org/0000-0003-3001-676X",
            "name": "Jonathan Sick",
        }
    ]

    # The entry that is neither a part nor in the footer reaches no page's
    # site-wide block.
    assert UNLISTED_DOI not in json.dumps(payload)


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
    # There is no page URL to state, so the full-text tag is omitted rather
    # than falling back to the doi.org redirect, which is not the full text.
    assert "citation_fulltext_html_url" not in _meta(doc)
    assert _jsonld(doc)["url"] == f"https://doi.org/{VISIT_DOI}"
