# type: ignore
"""Build tests for the citations a user guide shows in its page footer.

DataCite asks a DOI's landing page to display a full bibliographic citation
with the DOI written as a resolvable link. The ``citation-card`` directive is
the page-level surface for that; this is the site-wide one, rendered by
:file:`templates/pydata/rubin-footer.html` on every page of the guide.

The footer shows every ``[[project.citations]]`` entry whose ``in_footer`` is
set — the ``self`` entry by default, and the others opt in — in the order the
entries are declared. Everything it renders comes from the ``html_context``
the guide preset publishes; the template composes nothing itself.

These tests build the full user-guide stack twice, once for a site that
declares citations and once for one that declares none, because the rendered
footer is the only place the coupling between the configuration and the
template can be observed.
"""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from lxml import html
from sphinx.testing.util import SphinxTestApp

# Must match the [[project.citations]] entries in
# tests/roots/test-guide/documenteer.toml, in that file's order.
SELF_DOI_URL = "https://doi.org/10.71929/rubin/2570308"
DATASET_DOI_URL = "https://doi.org/10.5281/zenodo.10385500"
# The third entry sets in_footer = false, so the footer must not show it.
PAPER_DOI_URL = "https://doi.org/10.5281/zenodo.10385501"

CITATIONS = ".rubin-footer .rubin-footer__citations"
CITATION = ".rubin-footer__citation"
LABEL = ".rubin-footer__citation-label"
TEXT = ".rubin-footer__citation-text"
NOTE = ".rubin-footer__citation-note"
BIBTEX = ".rubin-footer__citation-bibtex"
BIBTEX_ENTRY = ".rubin-footer__citation-bibtex-entry"
COPY = ".rubin-footer__citation-copy"
COPY_STATUS = ".rubin-footer__citation-copy-status"

# The script that wires up every copy button, shipped through html_js_files
# only by a site that declares citations.
COPY_SCRIPT = "rubin-citation-copy.js"

# The BibTeX entry documenteer.citations composes for the first
# [[project.citations]] entry of tests/roots/test-guide/documenteer.toml.
SELF_BIBTEX = """@misc{veracrubinobservatory2025guide,
    author = {{Vera C. Rubin Observatory}},
    title = {{Guide Build Smoke Test}},
    year = {2025},
    publisher = {Vera C. Rubin Observatory},
    doi = {10.71929/rubin/2570308},
    url = {https://doi.org/10.71929/rubin/2570308}
}"""

_HAS_PYDATA = importlib.util.find_spec("pydata_sphinx_theme") is not None

pytestmark = pytest.mark.skipif(
    not _HAS_PYDATA, reason="pydata_sphinx_theme is not installed"
)


def _text(element: html.HtmlElement) -> str:
    """Return an element's text content, with whitespace collapsed."""
    return " ".join(element.text_content().split())


def _build(app: SphinxTestApp, page: str = "index.html") -> html.HtmlElement:
    """Build the site and parse one of its pages.

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
    return html.fromstring((app.outdir / page).read_text(encoding="utf-8"))


@pytest.mark.sphinx("html", testroot="guide", srcdir="guide-footer-citations")
def test_footer_shows_the_opted_in_citations(app: SphinxTestApp) -> None:
    """The footer shows the self citation and the entry that opted in, in the
    order documenteer.toml declares them, and omits the entry that opted out.
    """
    doc = _build(app)

    (block,) = doc.cssselect(CITATIONS)
    citations = block.cssselect(CITATION)
    assert len(citations) == 2, "only the in_footer entries should render"

    assert [_text(c.cssselect(LABEL)[0]) for c in citations] == [
        "Site",
        "Dataset",
    ]

    # The DOI is written as a resolvable https://doi.org/ link, which is what
    # makes the page a landing page rather than a page that merely names a
    # DOI.
    (site_link,) = citations[0].cssselect(f"{TEXT} a")
    assert site_link.get("href") == SELF_DOI_URL
    (dataset_link,) = citations[1].cssselect(f"{TEXT} a")
    assert dataset_link.get("href") == DATASET_DOI_URL
    assert dataset_link.text_content().strip() == DATASET_DOI_URL

    assert PAPER_DOI_URL not in html.tostring(block, encoding="unicode")


@pytest.mark.sphinx("html", testroot="guide", srcdir="guide-footer-citations")
def test_footer_citation_carries_the_full_record(app: SphinxTestApp) -> None:
    """Each footer citation shows the label, the plain-text citation ending
    in the linked DOI, and the entry's note.
    """
    doc = _build(app)

    (block,) = doc.cssselect(CITATIONS)
    site = block.cssselect(CITATION)[0]

    assert _text(site.cssselect(LABEL)[0]) == "Site"
    assert _text(site.cssselect(TEXT)[0]) == (
        "Vera C. Rubin Observatory (2025). Guide Build Smoke Test. "
        f"Vera C. Rubin Observatory. {SELF_DOI_URL}"
    )
    assert _text(site.cssselect(NOTE)[0]) == "Cite this documentation."


@pytest.mark.sphinx("html", testroot="guide", srcdir="guide-footer-citations")
def test_footer_citation_escapes_its_markup(app: SphinxTestApp) -> None:
    """A citation field containing an ampersand is escaped on its way into the
    page.

    Sphinx's Jinja environment has no autoescaping, so the footer template
    escapes every value it interpolates itself; a title with a ``&`` or a
    ``<`` in it must not reach the page as raw markup.
    """
    _build(app)
    raw = (app.outdir / "index.html").read_text(encoding="utf-8")

    assert "Smoke Test Images &amp; Catalogs" in raw
    assert "Smoke Test Images & Catalogs" not in raw


@pytest.mark.sphinx("html", testroot="guide", srcdir="guide-footer-citations")
def test_footer_citations_render_on_every_page(app: SphinxTestApp) -> None:
    """The footer is site-wide, so a page that carries no citation-card still
    shows the citations.
    """
    doc = _build(app, page="hidden.html")

    (block,) = doc.cssselect(CITATIONS)
    assert len(block.cssselect(CITATION)) == 2


@pytest.mark.sphinx(
    "html", testroot="guide-nocitations", srcdir="guide-footer-nocitations"
)
def test_guide_without_citations_renders_no_block(
    app: SphinxTestApp,
) -> None:
    """A guide that declares no [[project.citations]] renders the footer
    exactly as before: the nav, copyright, and funding statement, and no
    citations block at all.
    """
    doc = _build(app)

    (footer,) = doc.cssselect(".rubin-footer")
    assert not footer.cssselect(".rubin-footer__citations")
    assert not footer.cssselect(CITATION)
    # The rest of the footer is untouched.
    assert footer.cssselect(".rubin-footer__nav")
    assert footer.cssselect(".rubin-footer__funding")
    assert footer.cssselect(".rubin-footer__partner-logos")


@pytest.mark.sphinx("html", testroot="guide", srcdir="guide-footer-citations")
def test_footer_citation_offers_the_bibtex_entry(app: SphinxTestApp) -> None:
    """Each footer citation carries the same collapsed BibTeX disclosure the
    card does — the entry, a copy button, and a live region — so the two
    surfaces stay identical.
    """
    doc = _build(app)

    (block,) = doc.cssselect(CITATIONS)
    citations = block.cssselect(CITATION)
    assert len(citations) == 2

    for citation in citations:
        (details,) = citation.cssselect(BIBTEX)
        assert details.tag == "details"
        assert details.get("open") is None, "the entry starts collapsed"

        (summary,) = details.cssselect("summary")
        assert _text(summary) == "BibTeX"

        (button,) = details.cssselect(COPY)
        assert button.get("type") == "button"
        assert _text(button) == "Copy BibTeX"

        (status,) = details.cssselect(COPY_STATUS)
        assert status.get("aria-live") == "polite"

    # Byte-for-byte: what the reader copies is pasted straight into a .bib
    # file, so a stray leading newline is a broken entry.
    (pre,) = citations[0].cssselect(BIBTEX_ENTRY)
    assert pre.tag == "pre"
    assert pre.text_content() == SELF_BIBTEX


@pytest.mark.sphinx("html", testroot="guide", srcdir="guide-footer-citations")
def test_footer_bibtex_escapes_its_markup(app: SphinxTestApp) -> None:
    """A BibTeX entry reaches the page escaped, like every other value the
    footer interpolates: the second entry's title carries a LaTeX-escaped
    ampersand.
    """
    _build(app)
    raw = (app.outdir / "index.html").read_text(encoding="utf-8")

    assert r"Smoke Test Images \&amp; Catalogs" in raw
    assert r"Smoke Test Images \& Catalogs" not in raw


@pytest.mark.sphinx("html", testroot="guide", srcdir="guide-footer-citations")
def test_guide_with_citations_ships_the_copy_script(
    app: SphinxTestApp,
) -> None:
    """The copy script is shipped and referenced on every page, so the buttons
    on the card and in the footer both work wherever they appear.
    """
    doc = _build(app, page="hidden.html")

    assert (app.outdir / "_static" / COPY_SCRIPT).is_file()
    # Sphinx appends a cache-busting ?v= query to the src, so match the path.
    scripts = [script.get("src") or "" for script in doc.cssselect("script")]
    assert any(f"_static/{COPY_SCRIPT}" in src for src in scripts)


@pytest.mark.sphinx(
    "html", testroot="guide-nocitations", srcdir="guide-footer-nocitations"
)
def test_guide_without_citations_ships_no_copy_script(
    app: SphinxTestApp,
) -> None:
    """A guide with no citations has nothing to copy, so it neither ships the
    script nor references it.
    """
    doc = _build(app)

    assert not (app.outdir / "_static" / COPY_SCRIPT).exists()
    scripts = [script.get("src") or "" for script in doc.cssselect("script")]
    assert not any(COPY_SCRIPT in src for src in scripts)
