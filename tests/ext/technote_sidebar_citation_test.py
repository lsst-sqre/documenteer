# type: ignore
"""Build tests for the citation surface a technote shows in its sidebar.

A technote registered with a DOI is that DOI's landing page, and DataCite
asks such a page to display the DOI as a resolvable link alongside a full
bibliographic record. The technote's sidebar is where it says so: the DOI as
a ``https://doi.org/`` hyperlink, and the BibTeX entry with a button that
copies it.

Everything rendered comes from the ``html_context`` that
``documenteer.conf.technote`` publishes; the template composes nothing
itself. These tests build the whole technote stack twice, once for a
technote with a DOI and once for one without, because the rendered sidebar is
the only place the coupling between the preset, the theme's template names,
and the component can be observed.
"""

from __future__ import annotations

from io import StringIO

import pytest
from lxml import html
from sphinx.testing.util import SphinxTestApp

DOI_URL = "https://doi.org/10.71929/rubin/2570545"

SECTION = ".technote-sidebar-citation"
DOI = ".technote-sidebar-citation__doi"
BIBTEX = ".technote-sidebar-citation__bibtex"
BIBTEX_ENTRY = ".technote-sidebar-citation__bibtex-entry"
COPY = ".technote-sidebar-citation__copy"
COPY_STATUS = ".technote-sidebar-citation__copy-status"

# The script that wires up the copy button, shared with the guide's citation
# surfaces and shipped only by a technote that has a DOI.
COPY_SCRIPT = "rubin-citation-copy.js"

# What documenteer.citations composes from
# tests/roots/test-technote-citation/technote.toml, with the title taken from
# the document's H1.
BIBTEX_ENTRY_TEXT = """@techreport{sick2025technote,
    author = {Sick, Jonathan and Lovelace, Ada},
    title = {{Technote Citation Surfaces Test}},
    year = {2025},
    institution = {Vera C. Rubin Observatory},
    number = {SQR-000},
    doi = {10.71929/rubin/2570545},
    url = {https://sqr-000.lsst.io/}
}"""


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


def _script_sources(doc: html.HtmlElement) -> list[str]:
    """Return the ``src`` of every script the page links."""
    return [script.get("src") or "" for script in doc.cssselect("script")]


def _build(app: SphinxTestApp) -> html.HtmlElement:
    """Build the technote and parse its page."""
    app.build()
    return html.fromstring((app.outdir / "index.html").read_text("utf-8"))


@pytest.mark.sphinx(
    "html", testroot="technote-citation", srcdir="technote-citation"
)
def test_sidebar_shows_the_doi_as_a_resolvable_link(
    app: SphinxTestApp,
) -> None:
    """The sidebar writes the DOI as a full https://doi.org/ hyperlink, which
    is what makes the page a landing page rather than one that merely names a
    DOI.
    """
    doc = _build(app)

    (section,) = doc.cssselect(SECTION)
    (link,) = section.cssselect(f"{DOI} .technote-icon-metadata__value a")
    assert link.get("href") == DOI_URL
    assert _text(link) == DOI_URL


@pytest.mark.sphinx(
    "html", testroot="technote-citation", srcdir="technote-citation"
)
def test_sidebar_offers_the_bibtex_entry(app: SphinxTestApp) -> None:
    """The sidebar carries the same collapsed BibTeX disclosure the guide's
    citation surfaces do — the entry, a copy button, and a live region — so
    the surfaces read identically.
    """
    doc = _build(app)

    (section,) = doc.cssselect(SECTION)
    (details,) = section.cssselect(BIBTEX)
    assert details.tag == "details"
    assert details.get("open") is None, "the entry starts collapsed"

    (summary,) = details.cssselect("summary")
    assert _text(summary) == "BibTeX"

    (button,) = details.cssselect(COPY)
    assert button.get("type") == "button"

    (status,) = details.cssselect(COPY_STATUS)
    assert status.get("aria-live") == "polite"


@pytest.mark.sphinx(
    "html", testroot="technote-citation", srcdir="technote-citation"
)
def test_the_embedded_entry_is_what_the_reader_copies(
    app: SphinxTestApp,
) -> None:
    """The <pre> holds the only copy of the entry, byte for byte: it is what
    rubin-citation-copy.js reads and what a reader selects when no script
    runs, so a stray leading newline is a broken entry.
    """
    doc = _build(app)

    (pre,) = doc.cssselect(BIBTEX_ENTRY)
    assert pre.tag == "pre"
    assert pre.text_content() == BIBTEX_ENTRY_TEXT


@pytest.mark.sphinx(
    "html", testroot="technote-citation", srcdir="technote-citation"
)
def test_the_copy_script_is_shipped(app: SphinxTestApp) -> None:
    """The copy button only works because the preset ships the shared script
    and the page loads it.
    """
    doc = _build(app)

    assert (app.outdir / "_static" / COPY_SCRIPT).is_file()
    # Sphinx appends a cache-busting ?v= query to every script it links.
    assert any(COPY_SCRIPT in source for source in _script_sources(doc))


@pytest.mark.sphinx(
    "html", testroot="technote-nocitation", srcdir="technote-nocitation"
)
def test_a_technote_without_a_doi_renders_nothing(
    app: SphinxTestApp, warning: StringIO
) -> None:
    """A technote with no DOI builds as it did before the surface existed:
    no component, no script, and no warnings.
    """
    doc = _build(app)

    assert not doc.cssselect(SECTION)
    assert not (app.outdir / "_static" / COPY_SCRIPT).exists()
    assert not any(COPY_SCRIPT in source for source in _script_sources(doc))
    # The rest of the sidebar is untouched.
    assert doc.cssselect(".technote-sidebar-section")
    assert _build_warnings(warning) == []


@pytest.mark.sphinx(
    "html", testroot="technote-citation", srcdir="technote-citation"
)
def test_the_citation_surface_builds_cleanly(
    app: SphinxTestApp, warning: StringIO
) -> None:
    """Rendering the surface warns about nothing."""
    _build(app)

    assert _build_warnings(warning) == []


@pytest.mark.sphinx(
    "html", testroot="technote-citation", srcdir="technote-citation"
)
def test_the_sidebar_still_shows_the_theme_sections(
    app: SphinxTestApp,
) -> None:
    """The citation section is added to the sidebar the theme composes, not
    in place of it: the logo, the version metadata, and the source links are
    all still there.
    """
    doc = _build(app)

    (sidebar,) = doc.cssselect(".technote-logo-container")
    headings = [
        _text(heading)
        for heading in sidebar.cssselect(".technote-sidebar-section__heading")
    ]
    assert headings == ["Version", "Source", "Cite"]
    assert sidebar.cssselect("img")
