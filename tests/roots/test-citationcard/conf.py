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

# myst_parser is here so the root can prove the role reaches a MyST
# document as ``{doi}``; a guide gets it from the configuration preset.
extensions = ["documenteer.ext.citationcard", "myst_parser"]

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
    # Keyed explicitly, so that a selector matching its key selects
    # something no spelling of its DOI does, and vice versa.
    GuideCitation(
        citation=Citation(
            title="Citation Card Test Report",
            doi="10.71929/rubin/2570309",
            authors=(RUBIN,),
            publisher="Vera C. Rubin Observatory",
            date=PartialDate(2025, 5, 1),
        ),
        label="Report",
        bibtex_key="RTN-115",
    ),
    # Two entries under one label, which is the shape a site with one page
    # per data product has: the word the reader needs at that spot is the
    # same on every one of them, so the label repeats and the DOI or the key
    # is what tells the entries apart. Their keys are stated here because a
    # guide resolves a DOI-bearing entry's key to its DOI, and that
    # resolution runs over documenteer.toml rather than over the contexts
    # this root composes by hand.
    GuideCitation(
        citation=Citation(
            title="Test Object catalog (TAP)",
            doi="10.71929/rubin/3382539",
            authors=(RUBIN,),
            publisher="Vera C. Rubin Observatory",
            date=PartialDate(2025, 2, 3),
        ),
        label="TAP",
        bibtex_key="10.71929/rubin/3382539",
    ),
    GuideCitation(
        citation=Citation(
            title="Test Source catalog (TAP)",
            doi="10.71929/rubin/3382540",
            authors=(RUBIN,),
            publisher="Vera C. Rubin Observatory",
            date=PartialDate(2025, 2, 3),
        ),
        label="TAP",
        bibtex_key="10.71929/rubin/3382540",
    ),
    # Located by url rather than by a DOI, which is what a package that has
    # never been deposited looks like. The ``doi`` role has nothing to link
    # for it.
    GuideCitation(
        citation=Citation(
            title="Citation Card Test Package",
            url="https://github.com/lsst-sqre/documenteer",
            authors=(RUBIN,),
            publisher="Vera C. Rubin Observatory",
            date=PartialDate(2025, 3, 4),
        ),
        label="Software",
    ),
]

CITATION_CONTEXTS = [citation.to_html_context() for citation in CITATIONS]

html_context = {
    "documenteer_citations": CITATION_CONTEXTS,
    "documenteer_self_citation": CITATION_CONTEXTS[0],
    "documenteer_preferred_citation": CITATION_CONTEXTS[0],
}
