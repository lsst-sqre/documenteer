# type: ignore
"""Build tests for the citation a technote shows at the end of its article,
and for the machine-readable identifiers its ``<head>`` carries.

Every technote ends its article with a "Citing this document" section,
rendered through the theme's otherwise-empty
``sections/article-footer.html``: a full bibliographic citation a reader can
copy, ending in a hyperlink to the work -- its DOI where it has one, and its
canonical URL where it does not.

A technote registered with a DOI is additionally that DOI's landing page, and
DataCite asks such a page to state that identity in metadata a harvester can
read as well. Those tags are emitted by the ``technote`` package itself, and
are asserted here because Documenteer's preset is what decides a technote is
published this way -- and because they are the claim that stays DOI-only
while the displayed citation no longer is.

The text and the link both come from the ``html_context`` that
``documenteer.conf.technote`` publishes; the template composes nothing
itself.
"""

from __future__ import annotations

import json
from io import StringIO

import pytest
from lxml import html
from sphinx.testing.util import SphinxTestApp

DOI = "10.71929/rubin/2570545"
DOI_URL = f"https://doi.org/{DOI}"

SECTION = ".technote-article-citation"
HEADING = ".technote-article-citation__heading"
TEXT = ".technote-article-citation__text"

# What documenteer.citations composes from
# tests/roots/test-technote-citation/technote.toml, with the title taken from
# the document's H1 and the year from the date the technote was updated.
CITATION_TEXT = (
    "Sick, Jonathan; Lovelace, Ada (2025). "
    "Technote Citation Surfaces Test. "
    f"Vera C. Rubin Observatory. {DOI_URL}"
)


# What the same composition makes of tests/roots/test-technote-nocitation,
# which declares no DOI: the same reference, located by the canonical URL
# that identifies the technote in the absence of one.
NO_DOI_URL = "https://sqr-001.lsst.io/"
NO_DOI_CITATION_TEXT = (
    "Sick, Jonathan (2025). "
    "Technote Without a DOI Test. "
    f"Vera C. Rubin Observatory. {NO_DOI_URL}"
)


def _text(element: html.HtmlElement) -> str:
    """Return an element's text content, with whitespace collapsed."""
    return " ".join(element.text_content().split())


def _build_warnings(warning: StringIO) -> list[str]:
    """Return the build's warnings, less the one the test environment causes.

    A test root is copied to a throwaway directory that is no Git repository,
    so ``sphinx-last-updated-by-git`` always warns that it found no history
    there. That warning says nothing about the technote configuration under
    test, and it is the reason these builds assert on the warning stream
    rather than running under ``warningiserror``.
    """
    return [
        line
        for line in warning.getvalue().splitlines()
        if "WARNING" in line and "Error getting data from Git" not in line
    ]


def _build(app: SphinxTestApp) -> html.HtmlElement:
    """Build the technote and parse its page."""
    app.build()
    return html.fromstring((app.outdir / "index.html").read_text("utf-8"))


def _meta(doc: html.HtmlElement, name: str) -> str | None:
    """Return the content of the named ``<meta>`` tag, if the page has one."""
    tags = doc.cssselect(f'meta[name="{name}"]')
    return tags[0].get("content") if tags else None


def _json_ld(doc: html.HtmlElement) -> dict:
    """Return the page's schema.org JSON-LD document."""
    (script,) = doc.cssselect('script[type="application/ld+json"]')
    return json.loads(script.text_content())


@pytest.mark.sphinx(
    "html", testroot="technote-citation", srcdir="technote-citation"
)
def test_the_article_ends_with_the_citation(app: SphinxTestApp) -> None:
    """The end of the article carries the full bibliographic citation under
    a heading that says what it is for, which is what a reader copies into a
    bibliography.
    """
    doc = _build(app)

    (footer,) = doc.cssselect(".technote-article-footer-container")
    (section,) = footer.cssselect(SECTION)
    (heading,) = section.cssselect(HEADING)
    assert _text(heading) == "Citing this document"

    (text,) = section.cssselect(TEXT)
    # Uncollapsed, because the template's one job here is to put nothing
    # between the lead and the link it ends in: a newline or an indent there
    # would collapse away to the single space the citation already has, and
    # the reader would copy a reference with a gap in it.
    assert text.text_content() == CITATION_TEXT


@pytest.mark.sphinx(
    "html", testroot="technote-citation", srcdir="technote-citation"
)
def test_the_citation_hyperlinks_its_doi(app: SphinxTestApp) -> None:
    """The DOI at the end of the citation is a resolvable hyperlink rather
    than plain text: displaying it that way is what DataCite asks of a
    landing page.
    """
    doc = _build(app)

    (text,) = doc.cssselect(TEXT)
    (link,) = text.cssselect("a")
    assert link.get("href") == DOI_URL
    assert _text(link) == DOI_URL
    # The link is the tail of the citation, not a duplicate of it.
    assert _text(text).endswith(f". {DOI_URL}")


@pytest.mark.sphinx(
    "html", testroot="technote-citation", srcdir="technote-citation"
)
def test_the_head_states_the_doi_for_harvesters(app: SphinxTestApp) -> None:
    """Google Scholar reads Highwire tags and repository software reads
    Dublin Core, so the DOI is stated in both — bare for ``citation_doi``,
    and as the resolvable URL for ``DC.identifier``.
    """
    doc = _build(app)

    assert _meta(doc, "citation_doi") == DOI
    assert _meta(doc, "DC.identifier") == DOI_URL


@pytest.mark.sphinx(
    "html", testroot="technote-citation", srcdir="technote-citation"
)
def test_the_json_ld_identifies_the_technote_by_its_doi(
    app: SphinxTestApp,
) -> None:
    """The schema.org block names the DOI as the technote's identifier and
    as the node's own ``@id``, which is the DataCite-to-schema.org crosswalk
    a landing page is read through.
    """
    doc = _build(app)

    data = _json_ld(doc)
    assert data["@type"] == "Report"
    assert data["@id"] == DOI_URL
    assert data["identifier"] == {
        "@type": "PropertyValue",
        "propertyID": "DOI",
        "value": DOI,
        "url": DOI_URL,
    }


@pytest.mark.sphinx(
    "html", testroot="technote-nocitation", srcdir="technote-nocitation"
)
def test_a_technote_without_a_doi_is_cited_by_its_url(
    app: SphinxTestApp, warning: StringIO
) -> None:
    """A technote with no DOI ends its article with the same citation,
    located by its canonical URL: the URL a technote is served from is a
    stable identifier for it, so there is a reference to copy either way.
    """
    doc = _build(app)

    (footer,) = doc.cssselect(".technote-article-footer-container")
    (section,) = footer.cssselect(SECTION)
    (text,) = section.cssselect(TEXT)
    assert text.text_content() == NO_DOI_CITATION_TEXT

    (link,) = text.cssselect("a")
    assert link.get("href") == NO_DOI_URL

    assert _build_warnings(warning) == []


@pytest.mark.sphinx(
    "html", testroot="technote-nocitation", srcdir="technote-nocitation"
)
def test_a_technote_without_a_doi_claims_none_in_its_head(
    app: SphinxTestApp,
) -> None:
    """Displaying a citation is not claiming a DOI. A technote without one
    still states none in the metadata a harvester reads: no ``citation_doi``
    tag, and no ``identifier`` in the JSON-LD block, because that identity
    belongs to a registered work alone.
    """
    doc = _build(app)

    assert _meta(doc, "citation_doi") is None
    assert "identifier" not in _json_ld(doc)


@pytest.mark.sphinx(
    "html", testroot="technote-unlocated", srcdir="technote-unlocated"
)
def test_a_technote_with_nothing_to_link_is_cited_as_text(
    app: SphinxTestApp,
) -> None:
    """A technote that declares neither a DOI nor a ``canonical_url`` has no
    locator, so its citation ends after the publisher: a reference naming the
    work and its authors, with nothing hyperlinked.

    Every technote published to lsst.io declares a canonical URL, so this is
    the degenerate case. It is worth a build because the failure mode is a
    template writing an empty link -- or the word ``None`` -- into a citation
    a reader would copy.

    The build's warnings are not asserted on here: a technote that declares
    no ``canonical_url`` sets no ``html_baseurl``, which sphinx-sitemap
    warns about on its own account, and that warning is about the sitemap
    rather than about anything this root is built to show.
    """
    doc = _build(app)

    (section,) = doc.cssselect(SECTION)
    (text,) = section.cssselect(TEXT)
    assert text.text_content() == (
        "Sick, Jonathan (2025). "
        "Technote Without a Locator Test. "
        "Vera C. Rubin Observatory."
    )
    assert not text.cssselect("a")


@pytest.mark.sphinx(
    "html", testroot="technote-citation", srcdir="technote-citation"
)
def test_the_article_citation_builds_cleanly(
    app: SphinxTestApp, warning: StringIO
) -> None:
    """Rendering the surface warns about nothing."""
    _build(app)

    assert _build_warnings(warning) == []
