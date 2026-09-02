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
    srcdir="citationcard-noself",
    confoverrides={
        "html_context": {
            "documenteer_citations": [_dataset_context()],
            "documenteer_self_citation": None,
        }
    },
)
def test_missing_self_entry_warns(app: SphinxTestApp) -> None:
    """With no ``self`` entry, the default card warns and renders nothing,
    while a card that names a label still renders.
    """
    doc = _page(app, "index")

    (card,) = doc.cssselect(CARD)
    assert _text(card.cssselect(LABEL)[0]) == "Dataset"

    warnings = app.warning.getvalue()
    assert "no citation is marked" in warnings
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
