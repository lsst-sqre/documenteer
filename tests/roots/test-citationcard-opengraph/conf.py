"""Minimal Sphinx project pairing the ``citation-card`` directive with
sphinxext-opengraph, which is the pair the guide configuration preset sets up.

sphinxext-opengraph harvests a page's ``description`` and ``og:description``
by walking its doctree in document order, so where a card sits relative to
the page's prose is what these pages vary. The citations the directive reads
are composed into ``html_context`` here, the way
:file:`tests/roots/test-citationcard/conf.py` does, rather than through a
``documenteer.toml`` and the pydata theme.
"""

from documenteer.citations import (
    Citation,
    GuideCitation,
    OrganizationAuthor,
    PartialDate,
)

extensions = ["documenteer.ext.citationcard", "sphinxext.opengraph"]

exclude_patterns = ["_build"]

ogp_site_url = "https://example.lsst.io/"
# A social card is an image rendered with matplotlib. The tags under test are
# the text ones, so the pages ask for no image and the build stays small.
ogp_social_cards = {"enable": False}

CITATIONS = [
    GuideCitation(
        citation=Citation(
            title="Citation Card Test Site",
            doi="10.71929/rubin/2570308",
            authors=(OrganizationAuthor(name="Vera C. Rubin Observatory"),),
            publisher="Vera C. Rubin Observatory",
            date=PartialDate(2025, 6, 30),
        ),
        label="Site",
        is_self=True,
        is_preferred=True,
        in_footer=True,
        note="Cite this documentation.",
    ),
]

CITATION_CONTEXTS = [citation.to_html_context() for citation in CITATIONS]

html_context = {
    "documenteer_citations": CITATION_CONTEXTS,
    "documenteer_self_citation": CITATION_CONTEXTS[0],
    "documenteer_preferred_citation": CITATION_CONTEXTS[0],
}
