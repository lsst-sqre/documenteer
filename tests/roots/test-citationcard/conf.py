"""Minimal Sphinx project for the ``citation-card`` directive.

The directive reads the citations the guide preset publishes into
``html_context``, so this root builds that context from
`documenteer.citations` itself rather than through ``documenteer.toml`` and
the pydata theme. The contract under test is the html_context mapping, and
composing it here keeps the build small enough to exercise several
configurations.
"""

from documenteer.citations import (
    Citation,
    GuideCitation,
    OrganizationAuthor,
    PartialDate,
)

extensions = ["documenteer.ext.citationcard"]

exclude_patterns = ["_build"]

RUBIN = OrganizationAuthor(name="Vera C. Rubin Observatory")

CITATIONS = [
    GuideCitation(
        citation=Citation(
            title="Citation Card Test Site",
            doi="10.71929/rubin/2570308",
            authors=(RUBIN,),
            publisher="Vera C. Rubin Observatory",
            date=PartialDate(2025, 6, 30),
        ),
        label="Site",
        is_self=True,
        is_preferred=True,
        in_footer=True,
        note="Cite this documentation.",
    ),
    # No note, so the card's note element is absent rather than empty.
    GuideCitation(
        citation=Citation(
            title="Test Images & Catalogs",
            doi="10.5281/zenodo.10385500",
            authors=(RUBIN,),
            publisher="Vera C. Rubin Observatory",
            date=PartialDate(2025, 1, 15),
        ),
        label="Dataset",
    ),
]

CITATION_CONTEXTS = [citation.to_html_context() for citation in CITATIONS]

html_context = {
    "documenteer_citations": CITATION_CONTEXTS,
    "documenteer_self_citation": CITATION_CONTEXTS[0],
    "documenteer_preferred_citation": CITATION_CONTEXTS[0],
}
