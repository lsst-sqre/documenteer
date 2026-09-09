"""Minimal Sphinx project for the undated-citation build warning.

``documenteer.ext.citationdate`` reads the citations the guide preset
publishes into ``html_context``, so this root composes that context from
`documenteer.citations` itself rather than through :file:`documenteer.toml`
and the pydata theme. The contract under test is the mapping, and building it
here keeps the project small enough to carry every provenance a warning has to
describe -- inline, a CITATION.cff top-level record, and a CITATION.cff
preferred citation -- in one build.
"""

from documenteer.citations import (
    Citation,
    CitationType,
    GuideCitation,
    OrganizationAuthor,
    PartialDate,
)

extensions = ["documenteer.ext.citationdate"]

exclude_patterns = ["_build"]

RUBIN = OrganizationAuthor(name="Vera C. Rubin Observatory")

CITATIONS = [
    # Dated, so nothing is reported for it.
    GuideCitation(
        citation=Citation(
            title="Citation Date Test Site",
            doi="10.71929/rubin/2570308",
            authors=(RUBIN,),
            publisher="Vera C. Rubin Observatory",
            date=PartialDate(2025, 6, 30),
        ),
        label="Site",
        is_self=True,
        is_preferred=True,
    ),
    # Undated and stated inline, so documenteer.toml is the only place a date
    # could be set.
    GuideCitation(
        citation=Citation(
            title="Test Images & Catalogs",
            doi="10.5281/zenodo.10385500",
            authors=(RUBIN,),
            publisher="Vera C. Rubin Observatory",
        ),
        label="Dataset",
    ),
    # Undated and read from the top-level record of a CITATION.cff: a software
    # record with no date-released and no year anywhere in it. It carries a
    # DOI because that is the software the check reports -- a package located
    # only by its repository has no publication event to date and is exempt,
    # while a DOI's registration fixed a publication year that only has to be
    # written down. The type is the one CFF's default for a top-level record
    # resolves to.
    GuideCitation(
        citation=Citation(
            title="daf_butler",
            type=CitationType.software,
            doi="10.5281/zenodo.10161119",
            url="https://github.com/lsst/daf_butler",
            authors=(RUBIN,),
        ),
        label="Software",
        cff="../CITATION.cff",
        cff_preferred=False,
    ),
    # Undated, unlabelled, and read from a file's preferred citation, so the
    # warning has only the title to name the entry by.
    GuideCitation(
        citation=Citation(
            title="The Rubin Observatory Data Butler",
            doi="10.1117/12.2629569",
            authors=(RUBIN,),
        ),
        cff="../CITATION.cff",
    ),
]

CITATION_CONTEXTS = [citation.to_html_context() for citation in CITATIONS]

html_context = {
    "documenteer_citations": CITATION_CONTEXTS,
    "documenteer_self_citation": CITATION_CONTEXTS[0],
    "documenteer_preferred_citation": CITATION_CONTEXTS[0],
}
