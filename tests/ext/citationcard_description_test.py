# type: ignore
"""Tests for keeping a ``citation-card``'s text out of the page description
sphinxext-opengraph harvests.

sphinxext-opengraph composes a page's ``description`` and ``og:description``
from the page's own content in document order. A card near the top of a page
with little prose of its own would therefore publish an author list as the
page's summary, which is what :file:`tests/roots/test-citationcard-opengraph`
is shaped to catch: one page whose card comes first, and one whose prose
does.
"""

from __future__ import annotations

import importlib.util
import re

import pytest
from docutils import nodes
from sphinx.testing.util import SphinxTestApp

from documenteer.ext.citationcard import CARD_CLASS

_HAS_OPENGRAPH = importlib.util.find_spec("sphinxext.opengraph") is not None

# The prose of tests/roots/test-citationcard-opengraph/index.rst, which is
# all that page has to say for itself once its card is left out of the walk.
CARD_FIRST_DESCRIPTION = (
    "The card is the first body content on this page, so the citation is "
    "the first thing a description walk meets there."
)

# The prose of tests/roots/test-citationcard-opengraph/prose-first.rst, cut
# to sphinxext-opengraph's 200-character default. The prose overruns that
# length by itself, so this is the description the page published before the
# card was excluded as well as after.
PROSE_FIRST_DESCRIPTION = (
    "A page that introduces itself before it shows its citation, with "
    "prose long enough to fill the description sphinxext-opengraph "
    "harvests on its own, so that the description this page publishes "
    "is th..."
)

pytestmark = pytest.mark.skipif(
    not _HAS_OPENGRAPH, reason="sphinxext-opengraph is not installed"
)


def _meta_content(page: str, name: str, attribute: str = "property") -> str:
    """Return the content of the page's ``<meta>`` tag with this name."""
    match = re.search(
        rf'<meta {attribute}="{re.escape(name)}" content="([^"]*)" />', page
    )
    assert match is not None, f"no {attribute}={name!r} meta tag on the page"
    return match.group(1)


def _cards(doctree: nodes.document) -> list[nodes.Element]:
    """Return the card containers in a doctree, in document order."""
    return [
        node
        for node in doctree.findall(nodes.container)
        if CARD_CLASS in node["classes"]
    ]


@pytest.mark.sphinx(
    "html",
    testroot="citationcard-opengraph",
    srcdir="citationcard-opengraph-card-first",
)
def test_card_first_page_describes_itself_with_its_prose(
    app: SphinxTestApp,
) -> None:
    """A page whose first body content is a card takes its description from
    the prose around the card rather than from the card's citation.
    """
    app.build()
    page = (app.outdir / "index.html").read_text(encoding="utf-8")

    assert _meta_content(page, "og:description") == CARD_FIRST_DESCRIPTION
    assert (
        _meta_content(page, "description", attribute="name")
        == CARD_FIRST_DESCRIPTION
    )


@pytest.mark.sphinx(
    "html",
    testroot="citationcard-opengraph",
    srcdir="citationcard-opengraph-prose-first",
)
def test_prose_first_page_keeps_its_description(
    app: SphinxTestApp,
) -> None:
    """A page with prose before its card publishes the same description it
    published before the card's text was excluded.
    """
    app.build()
    page = (app.outdir / "prose-first.html").read_text(encoding="utf-8")

    assert _meta_content(page, "og:description") == PROSE_FIRST_DESCRIPTION
    assert (
        _meta_content(page, "description", attribute="name")
        == PROSE_FIRST_DESCRIPTION
    )


@pytest.mark.sphinx(
    "html",
    testroot="citationcard-opengraph",
    srcdir="citationcard-opengraph-doctree",
)
def test_the_doctree_still_carries_its_cards(app: SphinxTestApp) -> None:
    """Excluding the cards from the description walk leaves the doctree as it
    found it, so a later ``html-page-context`` handler still sees them.
    """
    seen: dict[str, int] = {}

    def record(
        app_: SphinxTestApp,
        pagename: str,
        templatename: str,
        context: dict,
        doctree: nodes.document | None,
    ) -> None:
        if doctree is not None:
            seen[pagename] = len(_cards(doctree))

    app.connect("html-page-context", record, priority=900)
    app.build()

    assert seen["index"] == 1
    assert seen["prose-first"] == 1
