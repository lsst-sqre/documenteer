"""Tests for composing a technote's own citation from its metadata."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from technote.metadata.model import Citation as TechnoteCitationMetadata
from technote.metadata.model import (
    Organization,
    Person,
    Status,
    StructuredName,
    TechnoteMetadata,
    TechnoteState,
)

from documenteer.conf._technotecitation import TechnoteCitation


def make_metadata(
    *,
    doi: str | None = "10.71929/rubin/2570545",
    title: str = "The Technote Title",
) -> TechnoteMetadata:
    """Build technote metadata shaped like a Rubin technote's."""
    return TechnoteMetadata(
        title=title,
        status=Status(state=TechnoteState.stable, note=None),
        canonical_url="https://sqr-000.lsst.io/",
        id="SQR-000",
        series_id="SQR",
        date_created=datetime(2024, 1, 2, tzinfo=UTC),
        date_updated=datetime(2025, 6, 30, 12, 0, tzinfo=UTC),
        version="1.0.0",
        authors=[
            Person(
                name=StructuredName(given="Jonathan", family="Sick"),
                orcid="https://orcid.org/0000-0003-3001-676X",
                affiliations=[Organization(name="Rubin Observatory")],
            ),
            Person(name=StructuredName(given="Ada", family="Lovelace")),
        ],
        organization=Organization(name="Vera C. Rubin Observatory"),
        citation=(None if doi is None else TechnoteCitationMetadata(doi=doi)),
    )


def test_doi_url_is_the_resolvable_form() -> None:
    """The DOI is offered as the full https://doi.org/ URL DataCite asks a
    landing page to display.
    """
    citation = TechnoteCitation(make_metadata())

    assert citation.doi_url == "https://doi.org/10.71929/rubin/2570545"


def test_bibtex_is_a_techreport_entry() -> None:
    """A technote composes as a BibTeX ``techreport``: its publisher is the
    institution, and its handle is the report number.
    """
    citation = TechnoteCitation(make_metadata())

    assert citation.bibtex == (
        "@techreport{sick2025the,\n"
        "    author = {Sick, Jonathan and Lovelace, Ada},\n"
        "    title = {{The Technote Title}},\n"
        "    year = {2025},\n"
        "    institution = {Vera C. Rubin Observatory},\n"
        "    number = {SQR-000},\n"
        "    doi = {10.71929/rubin/2570545},\n"
        "    url = {https://sqr-000.lsst.io/}\n"
        "}"
    )


def test_plain_text_is_the_datacite_display_citation() -> None:
    """The plain-text citation is DataCite's recommended display form —
    creators, year, title, publisher, then the DOI as a resolvable URL — so
    a reader can copy the whole line into a bibliography.
    """
    citation = TechnoteCitation(make_metadata())

    assert citation.plain_text == (
        "Sick, Jonathan; Lovelace, Ada (2025). The Technote Title. "
        "Vera C. Rubin Observatory. "
        "https://doi.org/10.71929/rubin/2570545"
    )


def test_plain_text_lead_stops_where_the_doi_link_begins() -> None:
    """The lead is the citation up to the DOI URL it ends in, so a template
    can hyperlink the DOI by writing the lead and then the link — never by
    doing string surgery of its own. Concatenating the two reproduces the
    citation exactly.
    """
    citation = TechnoteCitation(make_metadata())

    assert citation.plain_text_lead + citation.doi_url == citation.plain_text


@pytest.mark.parametrize(
    "attribute", ["doi_url", "bibtex", "plain_text", "plain_text_lead"]
)
def test_a_technote_without_a_doi_composes_nothing(attribute: str) -> None:
    """Nothing is composed for a technote that has no DOI, which is what
    keeps its pages free of an empty citation surface.
    """
    citation = TechnoteCitation(make_metadata(doi=None))

    assert getattr(citation, attribute) is None
