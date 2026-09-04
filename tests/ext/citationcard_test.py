# type: ignore
"""Tests for the ``citation-card`` directive.

The directive renders one of the site's ``[[project.citations]]`` entries as a
card: the full plain-text citation with its DOI hyperlinked, the entry's label,
and its note. It reads the citations the guide preset publishes into
``html_context`` and composes nothing itself, so these tests build a minimal
project whose ``conf.py`` populates that context directly (see
:file:`tests/roots/test-citationcard/conf.py`) and vary it with confoverrides.
"""

from __future__ import annotations

from typing import Any

import pytest
from lxml import html
from sphinx.testing.util import SphinxTestApp

from documenteer.citations import (
    Citation,
    GuideCitation,
    OrganizationAuthor,
    PartialDate,
)

# Must match tests/roots/test-citationcard/conf.py.
SELF_DOI_URL = "https://doi.org/10.71929/rubin/2570308"
DATASET_DOI_URL = "https://doi.org/10.5281/zenodo.10385500"
SELF_CITATION = (
    "Vera C. Rubin Observatory (2025). Citation Card Test Site. "
    f"Vera C. Rubin Observatory. {SELF_DOI_URL}"
)
DATASET_CITATION = (
    "Vera C. Rubin Observatory (2025). Test Images & Catalogs. "
    f"Vera C. Rubin Observatory. {DATASET_DOI_URL}"
)

CARD = ".documenteer-citation-card"
LABEL = ".documenteer-citation-card__label"
CITATION = ".documenteer-citation-card__citation"
NOTE = ".documenteer-citation-card__note"
BIBTEX = ".documenteer-citation-card__bibtex"
BIBTEX_ENTRY = ".documenteer-citation-card__bibtex-entry"
COPY = ".documenteer-citation-card__copy"
COPY_STATUS = ".documenteer-citation-card__copy-status"

# The BibTeX entries documenteer.citations composes for the two citations the
# test root declares; the card must show these bytes for bytes, since what a
# reader copies is pasted straight into a .bib file.
SELF_BIBTEX = """@misc{veracrubinobservatory2025citation,
    author = {{Vera C. Rubin Observatory}},
    title = {{Citation Card Test Site}},
    year = {2025},
    publisher = {Vera C. Rubin Observatory},
    doi = {10.71929/rubin/2570308},
    url = {https://doi.org/10.71929/rubin/2570308}
}"""
DATASET_BIBTEX = r"""@misc{veracrubinobservatory2025test,
    author = {{Vera C. Rubin Observatory}},
    title = {{Test Images \& Catalogs}},
    year = {2025},
    publisher = {Vera C. Rubin Observatory},
    doi = {10.5281/zenodo.10385500},
    url = {https://doi.org/10.5281/zenodo.10385500}
}"""

# The warning's type.subtype, as ``suppress_warnings`` spells it and as Sphinx
# appends it to the rendered message.
WARNING_NAME = "documenteer.citation_card"


def _dataset_context() -> dict[str, Any]:
    """Compose the html_context mapping for the test root's "Dataset"
    citation.

    Composed the same way the guide preset composes it, so a confoverride
    cannot drift from the contract the directive reads.
    """
    return GuideCitation(
        citation=Citation(
            title="Test Images & Catalogs",
            doi="10.5281/zenodo.10385500",
            authors=(OrganizationAuthor(name="Vera C. Rubin Observatory"),),
            publisher="Vera C. Rubin Observatory",
            date=PartialDate(2025, 1, 15),
        ),
        label="Dataset",
    ).to_html_context()


def _page(app: SphinxTestApp, name: str) -> html.HtmlElement:
    """Build the project and parse one of its pages."""
    app.build()
    return html.fromstring(
        (app.outdir / f"{name}.html").read_text(encoding="utf-8")
    )


def _text(element: html.HtmlElement) -> str:
    """Return the element's text content, with whitespace collapsed."""
    return " ".join(element.text_content().split())


@pytest.mark.sphinx("html", testroot="citationcard", srcdir="citationcard")
def test_default_card_renders_the_self_citation(app: SphinxTestApp) -> None:
    """``.. citation-card::`` with no argument renders the ``self`` entry: its
    label, the full citation with the DOI as a resolvable link, and the note.
    """
    doc = _page(app, "index")

    cards = doc.cssselect(CARD)
    assert len(cards) == 2, "the page declares two cards"
    card = cards[0]

    (label,) = card.cssselect(LABEL)
    assert _text(label) == "Site"

    (citation,) = card.cssselect(CITATION)
    assert _text(citation) == SELF_CITATION

    # The DOI is a hyperlink to itself, not bare text: DataCite asks a landing
    # page to display its DOI as a resolvable https://doi.org/ link.
    (link,) = citation.cssselect("a")
    assert link.get("href") == SELF_DOI_URL
    assert _text(link) == SELF_DOI_URL

    (note,) = card.cssselect(NOTE)
    assert _text(note) == "Cite this documentation."


@pytest.mark.sphinx("html", testroot="citationcard", srcdir="citationcard")
def test_card_carries_the_classes_the_stylesheet_targets(
    app: SphinxTestApp,
) -> None:
    """The card is a docutils container, so the HTML writer stamps ``docutils
    container`` on it alongside the card's own class.

    rubin-pydata-theme.scss chains all three to outweigh pydata-sphinx-theme's
    ``.docutils.container`` padding reset, so dropping either of the writer's
    classes here would silently flatten the card against its accent edge in a
    built site. :file:`tests/guide_stylesheet_test.py` pins the other half of
    that pair, the stylesheet's specificity.
    """
    doc = _page(app, "index")
    card = doc.cssselect(CARD)[0]

    assert {"documenteer-citation-card", "docutils", "container"} <= set(
        card.get("class").split()
    )


@pytest.mark.sphinx("html", testroot="citationcard", srcdir="citationcard")
def test_card_selects_an_entry_by_label(app: SphinxTestApp) -> None:
    """``.. citation-card:: Dataset`` renders the entry labelled "Dataset",
    and omits the note element entirely when the entry sets no note.
    """
    doc = _page(app, "index")

    card = doc.cssselect(CARD)[1]

    (label,) = card.cssselect(LABEL)
    assert _text(label) == "Dataset"

    (citation,) = card.cssselect(CITATION)
    assert _text(citation) == DATASET_CITATION
    (link,) = citation.cssselect("a")
    assert link.get("href") == DATASET_DOI_URL

    assert not card.cssselect(NOTE), (
        "an entry with no note renders no note element"
    )


def _preferred_paper_context() -> dict[str, Any]:
    """Compose the html_context mapping of a site whose preferred citation is
    a paper published elsewhere — the shape a repository whose CITATION.cff
    prefers a paper has, where the site is nobody's landing page.
    """
    return GuideCitation(
        citation=Citation(
            title="The Vera C. Rubin Observatory Data Butler",
            doi="10.1117/12.2629569",
            authors=(OrganizationAuthor(name="Vera C. Rubin Observatory"),),
            publisher="SPIE",
            date=PartialDate(2022, 8, 27),
        ),
        label="Paper",
        is_preferred=True,
        in_footer=True,
    ).to_html_context()


@pytest.mark.sphinx(
    "html",
    testroot="citationcard",
    srcdir="citationcard-preferred",
    confoverrides={
        "html_context": {
            "documenteer_citations": [_preferred_paper_context()],
            "documenteer_self_citation": None,
            "documenteer_preferred_citation": _preferred_paper_context(),
        }
    },
)
def test_default_card_renders_the_preferred_citation(
    app: SphinxTestApp,
) -> None:
    """A site that marks a citation ``preferred`` without claiming to be its
    landing page still has a default card, because the card asks which
    citation the site wants used, not whose landing page the site is.
    """
    doc = _page(app, "index")

    card = doc.cssselect(CARD)[0]
    (label,) = card.cssselect(LABEL)
    assert _text(label) == "Paper"

    assert "no citation is marked" not in app.warning.getvalue()


# Its own srcdir: a directive's warning is emitted while a page is *read*, so
# a test that asserts on one needs a build that has not already cached the
# page's doctree from an earlier test.
@pytest.mark.sphinx(
    "html", testroot="citationcard", srcdir="citationcard-unknown"
)
def test_unknown_label_warns_and_renders_nothing(app: SphinxTestApp) -> None:
    """An argument that matches no entry warns, naming the labels that are
    available, and renders no card and no docutils system message.
    """
    doc = _page(app, "unknown")

    assert not doc.cssselect(CARD)
    assert not doc.cssselect(".system-message"), (
        "the directive must not leave a system message in the page"
    )

    warnings = app.warning.getvalue()
    assert "Nonesuch" in warnings
    assert '"Site"' in warnings
    assert '"Dataset"' in warnings
    assert f"[{WARNING_NAME}]" in warnings, (
        "the warning must carry a type.subtype so that a -W build can "
        "suppress it by name"
    )


@pytest.mark.sphinx(
    "html",
    testroot="citationcard",
    srcdir="citationcard-suppressed",
    confoverrides={"suppress_warnings": [WARNING_NAME]},
)
def test_warning_is_suppressible(app: SphinxTestApp) -> None:
    """The warning is suppressible by name, so a ``-W`` build that knowingly
    carries an unresolved card can silence it rather than fail.
    """
    doc = _page(app, "unknown")

    assert not doc.cssselect(CARD)
    assert "Nonesuch" not in app.warning.getvalue()


@pytest.mark.sphinx(
    "html",
    testroot="citationcard",
    srcdir="citationcard-nopreferred",
    confoverrides={
        "html_context": {
            "documenteer_citations": [_dataset_context()],
            "documenteer_self_citation": None,
            "documenteer_preferred_citation": None,
        }
    },
)
def test_missing_preferred_entry_warns(app: SphinxTestApp) -> None:
    """With no preferred entry, the default card warns and renders nothing,
    while a card that names a label still renders.

    The advice names ``preferred``, since that is what a site whose citation
    is published elsewhere should set; ``self`` is offered only for a site
    that really is its DOI's landing page.
    """
    doc = _page(app, "index")

    (card,) = doc.cssselect(CARD)
    assert _text(card.cssselect(LABEL)[0]) == "Dataset"

    warnings = app.warning.getvalue()
    assert "preferred = true" in warnings
    assert "self = true" in warnings
    assert f"[{WARNING_NAME}]" in warnings


@pytest.mark.sphinx(
    "html",
    testroot="citationcard",
    srcdir="citationcard-nocitations",
    confoverrides={"html_context": {}},
)
def test_site_without_citations_warns(app: SphinxTestApp) -> None:
    """A site that declares no citations at all warns and renders nothing."""
    doc = _page(app, "index")

    assert not doc.cssselect(CARD)
    warnings = app.warning.getvalue()
    assert "project.citations" in warnings
    assert f"[{WARNING_NAME}]" in warnings


@pytest.mark.sphinx("html", testroot="citationcard", srcdir="citationcard")
def test_card_offers_the_bibtex_entry(app: SphinxTestApp) -> None:
    """Each card carries a collapsed BibTeX disclosure holding the entry the
    citation composes, plus a button that copies it.

    The reader pastes the entry into a ``.bib`` file of their own, which is
    why the affordance is a copy control rather than a download of a
    generated one-entry file.
    """
    doc = _page(app, "index")

    for card, expected in zip(
        doc.cssselect(CARD), [SELF_BIBTEX, DATASET_BIBTEX], strict=True
    ):
        (details,) = card.cssselect(BIBTEX)
        assert details.tag == "details"
        assert details.get("open") is None, "the entry starts collapsed"

        (summary,) = details.cssselect("summary")
        assert _text(summary) == "BibTeX"

        # Byte-for-byte: what the reader copies is pasted straight into a
        # bibliography, so a stray leading newline or an eaten backslash is a
        # broken entry.
        (pre,) = details.cssselect(BIBTEX_ENTRY)
        assert pre.tag == "pre"
        assert pre.text_content() == expected

        (button,) = details.cssselect(COPY)
        assert button.tag == "button"
        assert button.get("type") == "button", (
            "a bare <button> inside a form would submit it"
        )
        assert _text(button) == "Copy BibTeX"

        # The label swap alone is silent to a screen reader, so the outcome is
        # announced through a live region.
        (status,) = details.cssselect(COPY_STATUS)
        assert status.get("aria-live") == "polite"


@pytest.mark.sphinx("html", testroot="citationcard", srcdir="citationcard")
def test_card_bibtex_is_escaped(app: SphinxTestApp) -> None:
    r"""A BibTeX entry's markup characters are escaped on their way into the
    page rather than reaching it as raw HTML.

    A LaTeX-escaped ampersand (``\&``) in a title is ordinary, and a title
    could just as well hold a ``<``.
    """
    _page(app, "index")
    raw = (app.outdir / "index.html").read_text(encoding="utf-8")

    assert r"Test Images \&amp; Catalogs" in raw
    assert r"Test Images \& Catalogs" not in raw


def _unindent(text: str) -> str:
    """Strip each line's surrounding whitespace, so a block quoted at one
    indentation can be found inside output written at another.
    """
    return "\n".join(line.strip() for line in text.splitlines())


@pytest.mark.sphinx(
    "text", testroot="citationcard", srcdir="citationcard-text"
)
def test_card_bibtex_falls_back_to_a_literal_block(
    app: SphinxTestApp,
) -> None:
    """A non-HTML builder renders the BibTeX as a plain literal block.

    The disclosure, the button, and the live region are HTML affordances
    written by an HTML visitor, so a text or LaTeX build must show the entry
    itself rather than a wall of escaped markup.
    """
    app.build()
    text = _unindent((app.outdir / "index.txt").read_text(encoding="utf-8"))

    assert _unindent(SELF_BIBTEX) in text
    assert _unindent(DATASET_BIBTEX) in text
    assert "<details" not in text
    assert "<button" not in text
