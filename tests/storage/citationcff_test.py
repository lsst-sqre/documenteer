"""Tests for the documenteer.storage.citationcff module."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from documenteer.citations import (
    Citation,
    CitationType,
    OrganizationAuthor,
    PartialDate,
    PersonAuthor,
)
from documenteer.services.technotecff import TechnoteCffService
from documenteer.storage.citationcff import (
    CitationCffError,
    CitationCffNotFoundError,
    CitationCffParseError,
    read_citation_cff,
)
from tests.cffschema import assert_valid_cff

DATA_DIR = Path(__file__).parents[1] / "data" / "citationcff"


@pytest.mark.parametrize(
    "path", sorted(DATA_DIR.glob("*.cff")), ids=lambda path: path.name
)
def test_the_fixtures_are_valid_cff(path: Path) -> None:
    """Every file the reader is tested against satisfies CFF 1.2.0.

    A fixture that CFF itself would reject would pin the reader's behavior on
    a file no repository can have, so the shapes read here are validated
    against the same vendored schema the generated file is.
    """
    assert_valid_cff(yaml.safe_load(path.read_text(encoding="utf-8")))


def test_minimal_file() -> None:
    """A CFF file with only top-level fields composes a citation from
    them.
    """
    citation = read_citation_cff(DATA_DIR / "minimal.cff").citation

    assert citation.title == "Documenteer"
    assert citation.type is CitationType.software
    assert citation.doi == "10.5281/zenodo.10385500"
    assert citation.url == "https://documenteer.lsst.io/"
    assert citation.date == PartialDate(2026, 8, 24)
    assert citation.publisher is None
    assert citation.authors == (
        PersonAuthor(
            family_name="Sick",
            given_name="Jonathan",
            orcid="https://orcid.org/0000-0003-3001-676X",
            affiliation="Rubin Observatory Project Office",
        ),
    )


def test_preferred_citation_wins() -> None:
    """A preferred-citation supplies every field, mirroring GitHub's "Cite
    this repository" behavior, and its entity author and identifiers-array
    DOI both resolve.
    """
    citation = read_citation_cff(DATA_DIR / "preferred-citation.cff").citation

    assert citation.title == "The LSST DM Technical Note Publishing Platform"
    # The preferred citation's own type, not the software type the repository
    # stub above it declares.
    assert citation.type is CitationType.report
    assert citation.doi == "10.71929/rubin/2570308"
    assert citation.publisher == "Vera C. Rubin Observatory"
    assert citation.number == "SQR-000"
    assert citation.url == "https://sqr-000.lsst.io/"
    assert citation.date == PartialDate(2026, 8, 24)
    assert citation.authors == (
        OrganizationAuthor(name="Vera C. Rubin Observatory"),
        PersonAuthor(
            family_name="Sick",
            given_name="Jonathan",
            orcid="https://orcid.org/0000-0003-3001-676X",
        ),
    )


def test_the_preferred_citation_is_reported_as_the_record_read() -> None:
    """Reading a file that declares a preferred-citation says so, since the
    record read decides what the citation is *of*.

    A preferred citation is by construction a work other than the repository,
    so a caller that treats the citation as the repository's own — a site
    claiming to be its DOI's landing page, say — has to be able to tell the
    two records apart without parsing the file a second time.
    """
    record = read_citation_cff(DATA_DIR / "preferred-citation.cff")

    assert record.cited_preferred is True


def test_the_top_level_record_is_reported_as_not_preferred() -> None:
    """Both roads to the top-level record report it as the record read: a
    file that declares no preferred citation, and a caller that asked past
    the one it declares.

    The top level describes the repository itself, so a caller may treat
    either as the repository's own citation.
    """
    fallback = read_citation_cff(DATA_DIR / "minimal.cff")
    asked_for = read_citation_cff(
        DATA_DIR / "preferred-citation.cff", use_preferred_citation=False
    )

    assert fallback.cited_preferred is False
    assert asked_for.cited_preferred is False


def test_top_level_record_ignores_preferred_citation() -> None:
    """Asked for the file's own record, the reader returns the top-level
    software the repository is and never looks at preferred-citation.

    The title and the absent DOI are what say which record was read: the
    fixture declares no top-level type, as ``lsst/daf_butler``'s own file
    does, so the software type here is CFF's default for that record rather
    than something the file states.
    """
    citation = read_citation_cff(
        DATA_DIR / "software-record.cff", use_preferred_citation=False
    ).citation

    assert citation.title == "daf_butler"
    assert citation.type is CitationType.software
    assert citation.doi is None
    assert citation.authors == (
        OrganizationAuthor(name="Vera C. Rubin Observatory"),
        PersonAuthor(
            family_name="Jenness",
            given_name="Tim",
            orcid="https://orcid.org/0000-0001-5982-167X",
        ),
    )


def test_repository_code_stands_in_for_a_landing_page() -> None:
    """A record that states no landing page is located by its source
    repository, which is how CFF and GitHub cite software with no DOI.
    """
    citation = read_citation_cff(
        DATA_DIR / "software-record.cff", use_preferred_citation=False
    ).citation

    assert citation.url == "https://github.com/lsst/daf_butler"


def test_landing_page_beats_repository_code(tmp_path: Path) -> None:
    """A record that states both is located by its landing page: CFF's
    ``url`` is defined as the work's website, where ``repository-code`` is
    where its source is kept.
    """
    path = tmp_path / "CITATION.cff"
    path.write_text(
        "cff-version: 1.2.0\n"
        "title: A package\n"
        "type: software\n"
        "url: https://package.lsst.io/\n"
        "repository-code: https://github.com/lsst/package\n"
    )

    assert read_citation_cff(path).citation.url == "https://package.lsst.io/"


@pytest.mark.parametrize(
    ("cff_type", "expected"),
    [
        ("dataset", CitationType.dataset),
        ("database", CitationType.dataset),
        ("article", CitationType.article),
        ("conference-paper", CitationType.article),
        ("magazine-article", CitationType.article),
        ("software", CitationType.software),
        ("software-code", CitationType.software),
        ("report", CitationType.report),
        # CFF's vocabulary is far larger than Documenteer's, and a type with
        # no counterpart leaves the work untyped rather than guessing.
        ("thesis", None),
    ],
)
def test_type_is_mapped(
    tmp_path: Path, cff_type: str, expected: CitationType | None
) -> None:
    """A CFF record's own type is carried onto the citation, so an entry that
    points at the file is typed without restating the type.
    """
    path = tmp_path / "CITATION.cff"
    path.write_text(
        "cff-version: 1.2.0\n"
        "title: A work\n"
        f"type: {cff_type}\n"
        "doi: 10.71929/rubin/2570308\n"
    )

    assert read_citation_cff(path).citation.type is expected


def test_top_level_type_defaults_to_software(tmp_path: Path) -> None:
    """A top-level record that declares no type is read as software, which is
    the default CFF itself defines for the field.

    CFF restricts the top-level ``type`` to ``software`` or ``dataset`` and
    makes the key optional, so nearly every real file — a Zenodo- or
    GitHub-generated one, and ``lsst/daf_butler``'s — leaves it out and relies
    on the default. Reading such a record as untyped would compose it as a
    generic work rather than as the software the repository is.
    """
    path = tmp_path / "CITATION.cff"
    path.write_text(
        "cff-version: 1.2.0\n"
        "title: A package\n"
        "repository-code: https://github.com/lsst/package\n"
        "preferred-citation:\n"
        "  type: article\n"
        "  title: An article\n"
        "  doi: 10.1117/12.2629569\n"
    )

    citation = read_citation_cff(path, use_preferred_citation=False).citation

    assert citation.type is CitationType.software


def test_untyped_file_with_no_preference_is_software(tmp_path: Path) -> None:
    """A file that declares neither a preferred-citation nor a type is read as
    software as well, since the record the default read falls back to is that
    same top-level record.
    """
    path = tmp_path / "CITATION.cff"
    path.write_text(
        "cff-version: 1.2.0\n"
        "title: A package\n"
        "repository-code: https://github.com/lsst/package\n"
    )

    assert read_citation_cff(path).citation.type is CitationType.software


def test_untyped_preferred_citation_stays_untyped(tmp_path: Path) -> None:
    """A preferred-citation that declares no type leaves the work untyped.

    CFF gives a reference no default type and admits dozens of them, so the
    software default the top level carries would misreport whatever the file
    means to prefer.
    """
    path = tmp_path / "CITATION.cff"
    path.write_text(
        "cff-version: 1.2.0\n"
        "title: A package\n"
        "type: software\n"
        "preferred-citation:\n"
        "  title: An article\n"
        "  doi: 10.1117/12.2629569\n"
    )

    assert read_citation_cff(path).citation.type is None


def test_doi_url_is_normalized(tmp_path: Path) -> None:
    """A DOI written as a doi.org URL is normalized to its bare form."""
    path = tmp_path / "CITATION.cff"
    path.write_text(
        "cff-version: 1.2.0\n"
        "title: A dataset\n"
        "type: dataset\n"
        "doi: https://doi.org/10.71929/rubin/2570308\n"
    )

    assert read_citation_cff(path).citation.doi == "10.71929/rubin/2570308"


def test_publisher_preferred_over_institution(tmp_path: Path) -> None:
    """A reference's publisher is the citation's publisher; institution
    stands in when there is no publisher.
    """
    path = tmp_path / "CITATION.cff"
    path.write_text(
        "cff-version: 1.2.0\n"
        "title: A repository\n"
        "type: software\n"
        "preferred-citation:\n"
        "  type: article\n"
        "  title: An article\n"
        "  publisher:\n"
        "    name: A Publisher\n"
        "  institution:\n"
        "    name: An Institution\n"
    )

    assert read_citation_cff(path).citation.publisher == "A Publisher"


def test_year_and_month_stay_a_month(tmp_path: Path) -> None:
    """A reference that dates itself with year and month, as most published
    works do, yields a date stated to the month and no finer.
    """
    path = tmp_path / "CITATION.cff"
    path.write_text(
        "cff-version: 1.2.0\n"
        "title: A repository\n"
        "type: software\n"
        "preferred-citation:\n"
        "  type: article\n"
        "  title: An article\n"
        "  year: 2024\n"
        "  month: 6\n"
    )

    assert read_citation_cff(path).citation.date == PartialDate(2024, 6)


def test_name_particle_joins_the_family_name(tmp_path: Path) -> None:
    """A person's name-particle is carried with their family name, so the
    name cites as "van Dokkum, Pieter" rather than "Dokkum, Pieter".
    """
    path = tmp_path / "CITATION.cff"
    path.write_text(
        "cff-version: 1.2.0\n"
        "title: A repository\n"
        "type: software\n"
        "authors:\n"
        "  - family-names: Dokkum\n"
        "    name-particle: van\n"
        "    given-names: Pieter\n"
    )

    citation = read_citation_cff(path).citation
    assert citation.authors[0].citation_name == "van Dokkum, Pieter"


def test_missing_file(tmp_path: Path) -> None:
    """A missing file raises an error naming the path."""
    path = tmp_path / "CITATION.cff"

    with pytest.raises(CitationCffNotFoundError, match=re.escape(str(path))):
        read_citation_cff(path)


def test_invalid_yaml(tmp_path: Path) -> None:
    """A file that is not YAML raises an error naming the path."""
    path = tmp_path / "CITATION.cff"
    path.write_text("title: [unclosed\n")

    with pytest.raises(CitationCffParseError, match=re.escape(str(path))):
        read_citation_cff(path)


def test_not_a_mapping(tmp_path: Path) -> None:
    """YAML that is not a mapping is not a CFF file."""
    path = tmp_path / "CITATION.cff"
    path.write_text("- one\n- two\n")

    with pytest.raises(CitationCffParseError, match=re.escape(str(path))):
        read_citation_cff(path)


def test_missing_title(tmp_path: Path) -> None:
    """A file that names no work raises an error naming the path."""
    path = tmp_path / "CITATION.cff"
    path.write_text("cff-version: 1.2.0\ntype: software\n")

    with pytest.raises(CitationCffParseError, match=re.escape(str(path))):
        read_citation_cff(path)


def test_invalid_doi(tmp_path: Path) -> None:
    """A value that is not a DOI raises an error naming the path, rather
    than the bare ValueError the normalizer raises.
    """
    path = tmp_path / "CITATION.cff"
    path.write_text(
        "cff-version: 1.2.0\ntitle: A dataset\ntype: dataset\ndoi: nope\n"
    )

    with pytest.raises(CitationCffParseError, match=re.escape(str(path))):
        read_citation_cff(path)


def test_blank_url_falls_back_to_repository_code(tmp_path: Path) -> None:
    """A ``url`` that holds only whitespace states no landing page, so the
    record is located by its repository as one that omits the field is.

    Every CFF field is read through the same reduction, which treats a value
    that collapses to nothing as absent — so a blank one never reaches a
    citation as a location that composes to no link.
    """
    path = tmp_path / "CITATION.cff"
    path.write_text(
        "cff-version: 1.2.0\ntitle: A package\ntype: software\n"
        'url: "   "\n'
        "repository-code: https://github.com/lsst/package\n"
    )

    assert (
        read_citation_cff(path).citation.url
        == "https://github.com/lsst/package"
    )


def test_schemeless_url_rejected(tmp_path: Path) -> None:
    """A landing page written without a scheme raises an error naming the
    path, rather than reaching a rendered citation as a relative link.

    A CFF ``url`` and ``repository-code`` are both declared as URIs by the
    format's own schema, so a scheme-less one is already an invalid file; the
    reader says so rather than passing it through to a site's footer, where
    it would resolve against whatever page is being rendered.
    """
    path = tmp_path / "CITATION.cff"
    path.write_text(
        "cff-version: 1.2.0\ntitle: A package\ntype: software\n"
        "repository-code: github.com/lsst/package\n"
    )

    with pytest.raises(CitationCffParseError, match="not an absolute URL"):
        read_citation_cff(path)


def test_errors_share_a_base_class(tmp_path: Path) -> None:
    """Every failure is a CitationCffError, so a caller that only wants to
    report the path can catch one type.
    """
    with pytest.raises(CitationCffError):
        read_citation_cff(tmp_path / "CITATION.cff")


def test_round_trip_with_the_technote_generator(tmp_path: Path) -> None:
    """A CITATION.cff written by ``technote sync-cff`` reads back as the
    very citation it was written from, so the two directions cannot drift.
    """
    toml_path = tmp_path / "technote.toml"
    toml_path.write_text(
        "[technote]\n"
        'id = "SQR-000"\n'
        'title = "The LSST DM Technical Note Publishing Platform"\n'
        'canonical_url = "https://sqr-000.lsst.io/"\n'
        'doi = "10.71929/rubin/2570308"\n'
        "date_updated = 2026-08-24\n"
        "\n"
        "[technote.organization]\n"
        'name = "Vera C. Rubin Observatory"\n'
        "\n"
        "[[technote.authors]]\n"
        'name = {given = "Jonathan", family = "Sick"}\n'
        'orcid = "https://orcid.org/0000-0003-3001-676X"\n'
        "[[technote.authors.affiliations]]\n"
        'name = "Rubin Observatory Project Office"\n'
    )
    service = TechnoteCffService.from_technote_toml(toml_path)
    cff_path = tmp_path / "CITATION.cff"
    service.sync(cff_path)

    assert read_citation_cff(cff_path).citation == service.citation


def test_author_with_no_name(tmp_path: Path) -> None:
    """An author that spells no name raises an error that names the path
    once, rather than being re-wrapped by the DOI handler.
    """
    path = tmp_path / "CITATION.cff"
    path.write_text(
        "cff-version: 1.2.0\n"
        "title: A repository\n"
        "type: software\n"
        "authors:\n"
        "  - orcid: https://orcid.org/0000-0003-3001-676X\n"
    )

    with pytest.raises(CitationCffParseError) as excinfo:
        read_citation_cff(path)

    assert str(excinfo.value).count(str(path)) == 1


def test_malformed_preferred_citation(tmp_path: Path) -> None:
    """A preferred-citation that is present but is not a mapping is
    reported, rather than silently substituting the repository's own
    citation.
    """
    path = tmp_path / "CITATION.cff"
    path.write_text(
        "cff-version: 1.2.0\n"
        "title: A repository\n"
        "type: software\n"
        "doi: 10.5281/zenodo.10385500\n"
        "preferred-citation: Smith, J. 2024, An article\n"
    )

    with pytest.raises(CitationCffParseError) as excinfo:
        read_citation_cff(path)

    assert str(excinfo.value).count(str(path)) == 1
    assert "preferred-citation" in str(excinfo.value)


def test_null_preferred_citation_falls_back(tmp_path: Path) -> None:
    """A preferred-citation written with no value at all counts as absent,
    not as malformed: it holds no citation that could be silently dropped.
    """
    path = tmp_path / "CITATION.cff"
    path.write_text(
        "cff-version: 1.2.0\n"
        "title: A repository\n"
        "type: software\n"
        "doi: 10.5281/zenodo.10385500\n"
        "preferred-citation:\n"
    )

    assert read_citation_cff(path).citation.title == "A repository"


def test_a_bare_year_stays_a_year(tmp_path: Path) -> None:
    """A reference that states only a year keeps that precision, so the site
    that publishes it never asserts a day the file did not state.
    """
    path = tmp_path / "CITATION.cff"
    path.write_text(
        "cff-version: 1.2.0\n"
        "title: A repository\n"
        "type: software\n"
        "preferred-citation:\n"
        "  type: article\n"
        "  title: An article\n"
        "  year: 2022\n"
    )

    assert read_citation_cff(path).citation.date == PartialDate(2022)


def test_round_trip_of_a_reduced_precision_date(tmp_path: Path) -> None:
    """A citation dated only to a month survives the round trip through a
    generated CITATION.cff, which states such a date as year and month
    rather than as the full ``date-released`` CFF requires.
    """
    service = TechnoteCffService(
        Citation(
            title="An article",
            type=CitationType.report,
            date=PartialDate(2022, 8),
        )
    )
    path = tmp_path / "CITATION.cff"
    service.sync(path)

    assert read_citation_cff(path).citation == service.citation
