# type: ignore
"""Build tests for the citation a technote shows at the end of its article,
and for the machine-readable identifiers its ``<head>`` carries.

A technote registered with a DOI is that DOI's landing page. DataCite asks
such a page for two things: a full bibliographic citation a reader can copy,
with the DOI written as a resolvable link, and the same identity stated in
metadata a harvester can read. The first is the "Citing this document"
section rendered through the theme's otherwise-empty
``sections/article-footer.html``; the second is emitted by the ``technote``
package itself, and is asserted here because Documenteer's preset is what
decides a technote is published this way.

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
def test_a_technote_without_a_doi_ends_its_article_as_before(
    app: SphinxTestApp, warning: StringIO
) -> None:
    """A technote with no DOI builds as it did before the surface existed:
    the article footer the theme renders stays empty, no DOI is claimed in
    the head, and nothing warns.
    """
    doc = _build(app)

    (footer,) = doc.cssselect(".technote-article-footer-container")
    assert not footer.cssselect(SECTION)
    assert _text(footer) == ""

    assert _meta(doc, "citation_doi") is None
    assert "identifier" not in _json_ld(doc)

    assert _build_warnings(warning) == []


@pytest.mark.sphinx(
    "html", testroot="technote-citation", srcdir="technote-citation"
)
def test_the_article_citation_builds_cleanly(
    app: SphinxTestApp, warning: StringIO
) -> None:
    """Rendering the surface warns about nothing."""
    _build(app)

    assert _build_warnings(warning) == []
