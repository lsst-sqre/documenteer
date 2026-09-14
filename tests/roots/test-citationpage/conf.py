"""Minimal Sphinx project for the citation page-claim build checks.

``documenteer.ext.citationpage`` reads the citations the guide preset
publishes into ``html_context``, so this root composes that context from
`documenteer.citations` itself rather than through :file:`documenteer.toml`
and the pydata theme. What the checks read is the environment -- the
project's docnames, and the anchors its doctrees carry -- so the project is
built out of the anchor shapes a page can have rather than out of the guide's
rendering. The full stack's own build of the same extension lives in
``tests/roots/test-guide-citationpage``.
"""

from documenteer.citations import (
    Citation,
    CitationType,
    GuideCitation,
    OrganizationAuthor,
    PartialDate,
)

extensions = ["documenteer.ext.citationpage"]

exclude_patterns = ["_build"]

project = "Citation Page Test"

html_baseurl = "https://example.lsst.io"

RUBIN = OrganizationAuthor(name="Vera C. Rubin Observatory")


def _citation(title: str, doi: str) -> Citation:
    """Compose a dataset record, since only the page claim varies here."""
    return Citation(
        title=title,
        type=CitationType.dataset,
        doi=doi,
        authors=(RUBIN,),
        publisher="Vera C. Rubin Observatory",
        date=PartialDate(2025, 6, 30),
    )


CITATIONS = [
    # The site's own DOI, claiming no page inside the site.
    GuideCitation(
        citation=_citation("Citation Page Test Release", "10.71929/rubin/1"),
        label="Release",
        is_self=True,
        is_preferred=True,
    ),
    # An explicit ``.. _object-butler:`` target, which docutils propagates
    # onto the section after the anchor generated from the heading's text, so
    # the claimed anchor is the section's *second* id and is not the one the
    # table of contents records for it either.
    GuideCitation(
        citation=_citation("Object catalog (Butler)", "10.71929/rubin/2"),
        label="Butler",
        page="products",
        page_fragment="object-butler",
    ),
    # A heading's own generated anchor, with no explicit target near it.
    GuideCitation(
        citation=_citation("Object catalog (TAP)", "10.71929/rubin/3"),
        label="TAP",
        page="products",
        page_fragment="tap",
    ),
    # An anchor that page does not carry, on a page that does record explicit
    # targets, so the warning has some to name.
    GuideCitation(
        citation=_citation("Object catalog (renamed)", "10.71929/rubin/4"),
        label="Renamed",
        page="products",
        page_fragment="no-such-anchor",
    ),
    # An anchor a page with no explicit target of its own does not carry, so
    # the warning has none to name.
    GuideCitation(
        citation=_citation("Visit table", "10.71929/rubin/5"),
        label="Visit",
        page="unlabelled",
        page_fragment="no-such-anchor",
    ),
    # A fragment on a docname the project does not contain, which the docname
    # check already reports.
    GuideCitation(
        citation=_citation("Retired catalog", "10.71929/rubin/6"),
        label="Missing",
        page="products/missing",
        page_fragment="no-such-anchor",
    ),
]

CITATION_CONTEXTS = [citation.to_html_context() for citation in CITATIONS]

html_context = {
    "documenteer_citations": CITATION_CONTEXTS,
    "documenteer_self_citation": CITATION_CONTEXTS[0],
    "documenteer_preferred_citation": CITATION_CONTEXTS[0],
}
