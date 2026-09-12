"""Tests for composing a technote's own citation from its metadata."""

from __future__ import annotations

from datetime import UTC, datetime

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

# The metadata's resolved ``date_updated``, which is the one date a citation
# is dated by. ``technote`` resolves it before the metadata reaches here,
# from technote.toml when the file declares the field and from the published
# commit when it does not, so the citation reads one value either way.
DATE_UPDATED = datetime(2025, 6, 30, 12, 0, tzinfo=UTC)

# A second date, in a different year, for the tests that assert *which*
# value the citation read.
COMMIT_DATE = datetime(2031, 3, 4, 5, 6, tzinfo=UTC)


def make_metadata(
    *,
    doi: str | None = "10.71929/rubin/2570545",
    title: str = "The Technote Title",
    technote_id: str | None = "SQR-000",
    date_updated: datetime | None = DATE_UPDATED,
    canonical_url: str | None = "https://sqr-000.lsst.io/",
) -> TechnoteMetadata:
    """Build technote metadata shaped like a Rubin technote's."""
    return TechnoteMetadata(
        title=title,
        status=Status(state=TechnoteState.stable, note=None),
        canonical_url=canonical_url,
        id=technote_id,
        series_id="SQR",
        date_created=datetime(2024, 1, 2, tzinfo=UTC),
        date_updated=date_updated,
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


def make_citation(
    *,
    doi: str | None = "10.71929/rubin/2570545",
    title: str = "The Technote Title",
    technote_id: str | None = "SQR-000",
    date_updated: datetime | None = DATE_UPDATED,
    canonical_url: str | None = "https://sqr-000.lsst.io/",
) -> TechnoteCitation:
    """Compose the citation of a technote whose metadata carries a
    ``date_updated``, unless the test says it carries none.
    """
    return TechnoteCitation(
        make_metadata(
            doi=doi,
            title=title,
            technote_id=technote_id,
            date_updated=date_updated,
            canonical_url=canonical_url,
        )
    )


def _bibtex_key(citation: TechnoteCitation) -> str:
    """Return the citation key of a technote's BibTeX entry."""
    entry = citation.bibtex
    return entry.split("{", 1)[1].split(",", 1)[0]


def test_doi_url_is_the_resolvable_form() -> None:
    """The DOI is offered as the full https://doi.org/ URL DataCite asks a
    landing page to display.
    """
    citation = make_citation()

    assert citation.doi_url == "https://doi.org/10.71929/rubin/2570545"


def test_bibtex_is_a_techreport_entry() -> None:
    """A technote composes as a BibTeX ``techreport``: its publisher is the
    institution, and its handle is both the report number and the entry's
    citation key.
    """
    citation = make_citation()

    assert citation.bibtex == (
        "@techreport{SQR-000,\n"
        "    author = {Sick, Jonathan and Lovelace, Ada},\n"
        "    title = {{The Technote Title}},\n"
        "    year = {2025},\n"
        "    month = {June},\n"
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
    citation = make_citation()

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
    citation = make_citation()

    lead = citation.plain_text_lead
    doi_url = citation.doi_url
    assert doi_url is not None

    assert lead + doi_url == citation.plain_text


def test_a_technote_without_a_doi_is_cited_by_its_url() -> None:
    """A technote that declares no DOI is still citable, because its
    canonical URL is a stable locator for it.

    The citation ends in that URL where a registered technote's ends in its
    DOI, so the reference a reader copies resolves either way. This is how
    lsst-texmf's :file:`lsst.bib` already cites a DOI-less technote.
    """
    citation = make_citation(doi=None)

    assert citation.plain_text == (
        "Sick, Jonathan; Lovelace, Ada (2025). The Technote Title. "
        "Vera C. Rubin Observatory. "
        "https://sqr-000.lsst.io/"
    )


def test_a_technote_without_a_doi_keeps_the_handle_keyed_entry() -> None:
    """The BibTeX entry of a DOI-less technote is the same ``techreport``,
    keyed by the handle and located by the canonical URL, with no ``doi``
    field claiming a registration it does not have.

    This is the entry lsst-texmf's :file:`lsst.bib` already carries for such
    a technote, so a reader who copies it gets what they would have found
    there.
    """
    citation = make_citation(doi=None)

    assert citation.bibtex == (
        "@techreport{SQR-000,\n"
        "    author = {Sick, Jonathan and Lovelace, Ada},\n"
        "    title = {{The Technote Title}},\n"
        "    year = {2025},\n"
        "    month = {June},\n"
        "    institution = {Vera C. Rubin Observatory},\n"
        "    number = {SQR-000},\n"
        "    url = {https://sqr-000.lsst.io/}\n"
        "}"
    )


def test_a_technote_without_a_doi_offers_no_doi_url() -> None:
    """Only a registered technote has a DOI to show as one.

    ``doi_url`` is the DOI *as a DOI* — the sidebar's DOI line and the head
    metadata are the surfaces that make that claim — so it stays `None`
    where the citation's own location is the technote's URL.
    """
    citation = make_citation(doi=None)

    assert citation.doi_url is None
    assert citation.plain_text_url == "https://sqr-000.lsst.io/"


def test_the_lead_and_the_url_reproduce_a_url_located_citation() -> None:
    """A URL-located citation splits where a DOI-located one does, so a
    template hyperlinks the URL by writing the lead and then the link —
    never by doing string surgery of its own.
    """
    citation = make_citation(doi=None)

    lead = citation.plain_text_lead
    url = citation.plain_text_url
    assert url is not None

    assert lead + url == citation.plain_text


def test_a_technote_with_no_doi_and_no_url_is_cited_unlocated() -> None:
    """A technote that declares neither a DOI nor a ``canonical_url`` has no
    locator, and its citation simply ends after the publisher.

    Every technote published to lsst.io declares a canonical URL, so this is
    the degenerate case rather than a normal one. It degrades to a citation
    that names the work without claiming a location: nothing to hyperlink,
    no ``url`` field in the entry, and — the failure mode worth a test —
    no ``None`` written out as though it were one.
    """
    citation = make_citation(doi=None, canonical_url=None)

    assert citation.plain_text == (
        "Sick, Jonathan; Lovelace, Ada (2025). The Technote Title. "
        "Vera C. Rubin Observatory."
    )
    assert citation.plain_text_url is None
    assert citation.plain_text_lead == citation.plain_text
    assert citation.bibtex == (
        "@techreport{SQR-000,\n"
        "    author = {Sick, Jonathan and Lovelace, Ada},\n"
        "    title = {{The Technote Title}},\n"
        "    year = {2025},\n"
        "    month = {June},\n"
        "    institution = {Vera C. Rubin Observatory},\n"
        "    number = {SQR-000}\n"
        "}"
    )


def test_metadata_with_no_date_updated_leaves_the_citation_undated() -> None:
    """Metadata that carries no ``date_updated`` at all composes a citation
    with no year — not one dated by the build that rendered it.

    ``technote`` resolves the field for every technote it builds, so this is
    not a state a built technote reaches; it is what the composition falls
    back to rather than reaching for ``date_created`` or the clock, neither
    of which says anything true about when the work was published.
    """
    citation = make_citation(date_updated=None)

    assert citation.plain_text == (
        "Sick, Jonathan; Lovelace, Ada. The Technote Title. "
        "Vera C. Rubin Observatory. "
        "https://doi.org/10.71929/rubin/2570545"
    )
    assert citation.bibtex == (
        "@techreport{SQR-000,\n"
        "    author = {Sick, Jonathan and Lovelace, Ada},\n"
        "    title = {{The Technote Title}},\n"
        "    institution = {Vera C. Rubin Observatory},\n"
        "    number = {SQR-000},\n"
        "    doi = {10.71929/rubin/2570545},\n"
        "    url = {https://sqr-000.lsst.io/}\n"
        "}"
    )


def test_date_created_is_never_the_year_a_citation_is_dated_by() -> None:
    """The date the technote was *started* does not date its citation.

    ``date_created`` is the day someone opened the repository, which is
    neither the day the technote was published nor the day it was last
    revised — the same reason ``documenteer technote sync-cff`` leaves it out
    of the CITATION.cff release date. This citation reads ``date_updated`` or
    nothing.
    """
    metadata = make_metadata(date_updated=None)
    assert metadata.date_created is not None, (
        "the metadata must state a date_created, or this test asserts "
        "nothing about ignoring one"
    )

    citation = TechnoteCitation(metadata)

    assert str(metadata.date_created.year) not in citation.plain_text


def test_a_technote_outside_a_series_keeps_the_composed_key() -> None:
    """A technote whose metadata states no ``id`` has no handle to be keyed
    by, so its entry falls back to the key ``documenteer.citations`` composes
    from author, year, and title.

    Every Rubin technote belongs to a series and has a handle, so this is the
    case the fallback exists for: a technote built on the preset outside one
    is keyed by something a reader can cite, rather than by the nothing its
    metadata has to offer.
    """
    citation = make_citation(technote_id=None)

    assert citation.bibtex.startswith("@techreport{sick2025technote,\n")


def test_the_bibtex_key_does_not_move_with_the_technote() -> None:
    r"""Retitling a technote, changing who wrote it, or dropping its date
    leaves the BibTeX key alone, because the key is the handle and the handle
    is none of those things.

    This is what a handle key buys over a composed one. A key built from
    author, year, and title moves whenever any of the three does, so a reader
    who had already stored the entry would end up with a bibliography whose
    ``\cite`` no longer resolved.
    """
    metadata = make_metadata()
    original = _bibtex_key(TechnoteCitation(metadata))

    metadata.title = "A Thoroughly Rewritten Technote"
    metadata.authors = [
        Person(name=StructuredName(given="Ada", family="Lovelace"))
    ]
    metadata.date_updated = COMMIT_DATE
    revised = TechnoteCitation(metadata)

    assert original == "SQR-000"
    assert _bibtex_key(revised) == original


def test_a_derived_date_updated_dates_the_citation() -> None:
    """A technote that declares no ``date_updated`` is still cited by a date.

    ``technote`` resolves the field before the metadata reaches here: a
    declared value, else the committer date of the published commit. Both
    reach the citation the same way, which is what makes every dated surface
    on the page state the one reproducible date.
    """
    metadata = make_metadata()
    metadata.date_updated = COMMIT_DATE

    citation = TechnoteCitation(metadata)

    assert f"({COMMIT_DATE.year})." in citation.plain_text
