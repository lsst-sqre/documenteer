"""Tests for the documenteer.services.technotecff module."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml

from documenteer.citations import Citation, CitationType, PartialDate
from documenteer.services.technotecff import (
    CffStatus,
    TechnoteCffError,
    TechnoteCffService,
)

FULL_TOML = """
[technote]
id = "SQR-000"
series_id = "SQR"
title = "The LSST DM Technical Note Publishing Platform"
canonical_url = "https://sqr-000.lsst.io/"
github_url = "https://github.com/lsst-sqre/sqr-000"
doi = "10.71929/rubin/2570308"
date_updated = 2026-08-24

[technote.organization]
name = "Vera C. Rubin Observatory"
ror = "https://ror.org/048g3cy84"

[[technote.authors]]
name = {given = "Jonathan", family = "Sick"}
internal_id = "sickj"
orcid = "https://orcid.org/0000-0003-3001-676X"
[[technote.authors.affiliations]]
name = "Rubin Observatory Project Office"
internal_id = "RubinObs"
"""


STRING_NAME_TOML = (
    FULL_TOML
    + """
[[technote.authors]]
name = "Frossie Economou"
"""
)
"""A second author whose name is a string rather than a name table."""

STRING_AFFILIATION_TOML = (
    FULL_TOML
    + """
[[technote.authors]]
name = {given = "Frossie", family = "Economou"}
affiliations = ["Rubin Observatory"]
"""
)
"""A second author whose affiliations are strings rather than tables."""

CREATED_ONLY_TOML = FULL_TOML.replace(
    "date_updated = 2026-08-24", "date_created = 2016-05-02T20:47:13Z"
)
"""A technote dated only by the day it was started.

This is the common case: most technotes never declare ``date_updated``, and
``date_created`` is the day the document was begun, not the day it was
published.
"""


STRING_TECHNOTE_TOML = 'technote = "SQR-000"\n'

STRING_AUTHORS_TOML = """
[technote]
id = "SQR-000"
title = "A technote"
authors = "Jonathan Sick"
"""

STRING_ORGANIZATION_TOML = """
[technote]
id = "SQR-000"
title = "A technote"
organization = "Vera C. Rubin Observatory"
"""

STRING_AFFILIATIONS_TOML = """
[technote]
id = "SQR-000"
title = "A technote"

[[technote.authors]]
name = {given = "Jonathan", family = "Sick"}
affiliations = "Rubin Observatory"
"""


DOCS_PAGE = (
    Path(__file__).parents[2] / "docs" / "technotes" / "citation-file.rst"
)
"""The technote guide page that shows an example CITATION.cff."""


def read_documented_cff() -> str:
    """Read the example :file:`CITATION.cff` the technote guide shows.

    The page's example is captioned ``CITATION.cff``, which is what tells it
    apart from the ``.pre-commit-config.yaml`` block further down.
    """
    lines = DOCS_PAGE.read_text(encoding="utf-8").splitlines()
    block: list[str] = []
    for line in lines[lines.index("   :caption: CITATION.cff") + 1 :]:
        if not line.strip():
            # The generated file has no blank lines in it, so the first one
            # after the example has started ends the literal block.
            if block:
                break
            continue
        if not line.startswith("   "):
            break
        block.append(line[3:])
    return "".join(f"{line}\n" for line in block)


CFF_FILE_REQUIRED_KEYS = frozenset(
    {"authors", "cff-version", "message", "title"}
)
"""The keys CFF 1.2.0 requires of a file's top-level record."""

CFF_REFERENCE_REQUIRED_KEYS = frozenset({"authors", "title", "type"})
"""The keys CFF 1.2.0 requires of a reference, ``preferred-citation``
included."""

CFF_FILE_TYPES = frozenset({"software", "dataset"})
"""The only two values CFF 1.2.0 allows a file's top-level ``type``."""

CFF_REFERENCE_TYPES = frozenset(
    {"article", "dataset", "generic", "report", "software"}
)
"""The members of CFF 1.2.0's reference vocabulary this generator can write.

CFF's own list is far longer; these are the ones a `CitationType` maps onto.
"""


def assert_valid_cff(document: object) -> None:
    """Assert that a parsed CITATION.cff satisfies CFF 1.2.0.

    cffconvert, the reference validator, is deliberately not a test
    dependency: it pins ``jsonschema<4``, so adding it downgrades the
    ``jsonschema`` the rest of the environment resolves — Jupyter's notebook
    reader among it. This asserts the rules its schema states about the parts
    of a file this generator writes: which keys a file and a reference must
    carry, which types each allows, that every author names itself, and that
    a date is a date. A field dropped from the generated shape is therefore
    still caught.
    """
    assert isinstance(document, dict)
    assert document["cff-version"] == "1.2.0"
    assert not CFF_FILE_REQUIRED_KEYS - set(document)
    assert document.get("type", "software") in CFF_FILE_TYPES
    _assert_valid_cff_record(document)

    reference = document.get("preferred-citation")
    if reference is not None:
        assert isinstance(reference, dict)
        assert not CFF_REFERENCE_REQUIRED_KEYS - set(reference)
        assert reference["type"] in CFF_REFERENCE_TYPES
        _assert_valid_cff_record(reference)


def _assert_valid_cff_record(record: dict[str, object]) -> None:
    """Assert the constraints a file and a reference state alike."""
    authors = record["authors"]
    assert isinstance(authors, list)
    assert authors
    for author in authors:
        assert isinstance(author, dict)
        # A CFF entity names itself with `name`; a person with at least one
        # of the name fields. Either way, an author with no name at all is a
        # citation nobody is credited in.
        assert author.keys() & {"name", "family-names", "given-names"}
    if "date-released" in record:
        assert isinstance(record["date-released"], date)
    if "month" in record:
        assert 1 <= record["month"] <= 12  # type: ignore[operator]


def test_render_preferred_citation(tmp_path: Path) -> None:
    """A technote renders as a CFF 1.2.0 file whose preferred-citation is a
    report carrying the technote's DOI, number, publisher, and URL.
    """
    toml_path = tmp_path / "technote.toml"
    toml_path.write_text(FULL_TOML)

    service = TechnoteCffService.from_technote_toml(toml_path)
    text = service.render()

    assert text.startswith(
        "# Generated by documenteer technote sync-cff from technote.toml "
        "— do not edit\n"
    )

    document = yaml.safe_load(text)
    assert document["cff-version"] == "1.2.0"
    assert document["type"] == "software"
    assert document["title"] == (
        "The LSST DM Technical Note Publishing Platform"
    )

    reference = document["preferred-citation"]
    assert reference["type"] == "report"
    assert reference["title"] == (
        "The LSST DM Technical Note Publishing Platform"
    )
    assert reference["doi"] == "10.71929/rubin/2570308"
    assert reference["number"] == "SQR-000"
    assert reference["institution"] == {"name": "Vera C. Rubin Observatory"}
    assert reference["url"] == "https://sqr-000.lsst.io/"
    assert str(reference["date-released"]) == "2026-08-24"


def test_authors_round_trip(tmp_path: Path) -> None:
    """An author's ORCID and affiliation reach both author lists."""
    toml_path = tmp_path / "technote.toml"
    toml_path.write_text(FULL_TOML)

    document = yaml.safe_load(
        TechnoteCffService.from_technote_toml(toml_path).render()
    )

    author = {
        "family-names": "Sick",
        "given-names": "Jonathan",
        "orcid": "https://orcid.org/0000-0003-3001-676X",
        "affiliation": "Rubin Observatory Project Office",
    }
    assert document["authors"] == [author]
    assert document["preferred-citation"]["authors"] == [author]


def test_bare_orcid_becomes_a_url(tmp_path: Path) -> None:
    """CFF requires an ORCID as an orcid.org URL, whatever technote.toml
    spells it as.
    """
    toml_path = tmp_path / "technote.toml"
    toml_path.write_text(
        FULL_TOML.replace(
            'orcid = "https://orcid.org/0000-0003-3001-676X"',
            'orcid = "0000-0003-3001-676X"',
        )
    )

    document = yaml.safe_load(
        TechnoteCffService.from_technote_toml(toml_path).render()
    )

    assert (
        document["authors"][0]["orcid"]
        == "https://orcid.org/0000-0003-3001-676X"
    )


def test_prefixed_doi_is_normalized(tmp_path: Path) -> None:
    """A DOI spelled the way technote.toml also accepts it — a ``doi:``
    prefix and a space — reaches CITATION.cff in its bare form.
    """
    toml_path = tmp_path / "technote.toml"
    toml_path.write_text(
        FULL_TOML.replace(
            'doi = "10.71929/rubin/2570308"',
            'doi = "doi: 10.71929/rubin/2570308"',
        )
    )

    document = yaml.safe_load(
        TechnoteCffService.from_technote_toml(toml_path).render()
    )

    assert document["preferred-citation"]["doi"] == "10.71929/rubin/2570308"


def test_technote_without_doi(tmp_path: Path) -> None:
    """A technote with no DOI still generates a file; the DOI is omitted."""
    toml_path = tmp_path / "technote.toml"
    toml_path.write_text(
        FULL_TOML.replace('doi = "10.71929/rubin/2570308"\n', "")
    )

    document = yaml.safe_load(
        TechnoteCffService.from_technote_toml(toml_path).render()
    )

    assert "doi" not in document["preferred-citation"]
    assert document["preferred-citation"]["url"] == "https://sqr-000.lsst.io/"


def test_untitled_technote_falls_back_to_its_id(tmp_path: Path) -> None:
    """A technote that declares no title is titled by its ID, with a
    warning for the caller to report.
    """
    toml_path = tmp_path / "technote.toml"
    toml_path.write_text(
        FULL_TOML.replace(
            'title = "The LSST DM Technical Note Publishing Platform"\n', ""
        )
    )

    service = TechnoteCffService.from_technote_toml(toml_path)

    assert yaml.safe_load(service.render())["title"] == "SQR-000"
    assert len(service.warnings) == 1
    assert "no title" in service.warnings[0]


def test_status_and_sync(tmp_path: Path) -> None:
    """A CITATION.cff is absent, then current, and re-syncing leaves it
    byte-for-byte untouched.
    """
    toml_path = tmp_path / "technote.toml"
    toml_path.write_text(FULL_TOML)
    cff_path = tmp_path / "CITATION.cff"
    service = TechnoteCffService.from_technote_toml(toml_path)

    assert service.status(cff_path) is CffStatus.absent
    assert service.sync(cff_path) is CffStatus.absent
    assert service.status(cff_path) is CffStatus.current

    mtime = cff_path.stat().st_mtime_ns
    assert service.sync(cff_path) is CffStatus.current
    assert cff_path.stat().st_mtime_ns == mtime


def test_status_stale(tmp_path: Path) -> None:
    """A CITATION.cff that does not match technote.toml is stale."""
    toml_path = tmp_path / "technote.toml"
    toml_path.write_text(FULL_TOML)
    cff_path = tmp_path / "CITATION.cff"
    cff_path.write_text("cff-version: 1.2.0\n")

    service = TechnoteCffService.from_technote_toml(toml_path)

    assert service.status(cff_path) is CffStatus.stale
    assert service.sync(cff_path) is CffStatus.stale
    assert service.status(cff_path) is CffStatus.current


def test_malformed_doi_is_rejected(tmp_path: Path) -> None:
    """A DOI that is not a DOI is reported where the metadata is read."""
    toml_path = tmp_path / "technote.toml"
    toml_path.write_text(
        FULL_TOML.replace(
            'doi = "10.71929/rubin/2570308"', 'doi = "not-a-doi"'
        )
    )

    with pytest.raises(ValueError, match="Not a DOI"):
        TechnoteCffService.from_technote_toml(toml_path)


def test_string_name_is_reported(tmp_path: Path) -> None:
    """An author whose name is a string rather than a table is reported
    against the entry it comes from, rather than crashing the reader.
    """
    toml_path = tmp_path / "technote.toml"
    toml_path.write_text(STRING_NAME_TOML)

    with pytest.raises(TechnoteCffError) as exc_info:
        TechnoteCffService.from_technote_toml(toml_path)

    message = str(exc_info.value)
    assert "The name of [[technote.authors]] entry 2" in message
    assert "Frossie Economou" in message


def test_string_affiliation_is_reported(tmp_path: Path) -> None:
    """An affiliation written as a string rather than a table is reported
    against the entry, and the affiliation within it, that it comes from.
    """
    toml_path = tmp_path / "technote.toml"
    toml_path.write_text(STRING_AFFILIATION_TOML)

    with pytest.raises(TechnoteCffError) as exc_info:
        TechnoteCffService.from_technote_toml(toml_path)

    message = str(exc_info.value)
    assert "Affiliation 1 of [[technote.authors]] entry 2" in message
    assert "Rubin Observatory" in message


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        pytest.param(
            STRING_TECHNOTE_TOML,
            "[technote] in technote.toml is not a table",
            id="technote",
        ),
        pytest.param(
            STRING_ORGANIZATION_TOML,
            "[technote.organization] in technote.toml is not a table",
            id="organization",
        ),
        pytest.param(
            STRING_AUTHORS_TOML,
            "[[technote.authors]] in technote.toml is not an array",
            id="authors",
        ),
        pytest.param(
            STRING_AFFILIATIONS_TOML,
            "The affiliations list of [[technote.authors]] entry 1 in "
            "technote.toml is not an array",
            id="affiliations",
        ),
    ],
)
def test_wrong_toml_type_is_reported(
    tmp_path: Path, source: str, expected: str
) -> None:
    """A table or array written as a scalar is reported by name, rather than
    reaching a reader that assumes its shape.

    sync-cff deliberately reads technote.toml without the technote package's
    pydantic models, so nothing validates these shapes before this code sees
    them.
    """
    toml_path = tmp_path / "technote.toml"
    toml_path.write_text(source)

    with pytest.raises(TechnoteCffError) as exc_info:
        TechnoteCffService.from_technote_toml(toml_path)

    assert expected in str(exc_info.value)


def test_a_reduced_precision_date_is_written_as_year_and_month() -> None:
    """CFF's ``date-released`` is a full calendar date, so a citation dated
    only to a month is written with the ``year`` and ``month`` a CFF
    reference states such a date with — and reads back at that precision.
    """
    service = TechnoteCffService(
        Citation(
            title="An article",
            type=CitationType.report,
            date=PartialDate(2022, 8),
        )
    )

    reference = yaml.safe_load(service.render())["preferred-citation"]
    assert "date-released" not in reference
    assert reference["year"] == 2022
    assert reference["month"] == 8


def test_a_technote_dated_only_by_its_creation_carries_no_date(
    tmp_path: Path,
) -> None:
    """``date_created`` is the day the technote was started, not the day it
    was released, so a technote that declares only that one is written with
    no release date at all — and says so, rather than dating the citation to
    a day nobody published on.
    """
    toml_path = tmp_path / "technote.toml"
    toml_path.write_text(CREATED_ONLY_TOML)

    service = TechnoteCffService.from_technote_toml(toml_path)
    document = yaml.safe_load(service.render())

    assert "date-released" not in document
    reference = document["preferred-citation"]
    assert "date-released" not in reference
    assert "year" not in reference
    assert len(service.warnings) == 1
    assert "no date_updated" in service.warnings[0]


def test_the_top_level_record_carries_the_doi_and_the_date(
    tmp_path: Path,
) -> None:
    """A tool that reads only the top level — cffconvert, or Zenodo's GitHub
    integration — gets a dated, identified record rather than an anonymous
    one, so the DOI and release date the preferred citation carries are
    mirrored above it.
    """
    toml_path = tmp_path / "technote.toml"
    toml_path.write_text(FULL_TOML)

    document = yaml.safe_load(
        TechnoteCffService.from_technote_toml(toml_path).render()
    )

    assert document["doi"] == "10.71929/rubin/2570308"
    assert str(document["date-released"]) == "2026-08-24"


def test_a_technote_without_a_doi_omits_it_from_the_top_level(
    tmp_path: Path,
) -> None:
    """A technote that has no DOI yet mirrors nothing: the top level omits
    the field rather than carrying an empty one.
    """
    toml_path = tmp_path / "technote.toml"
    toml_path.write_text(
        FULL_TOML.replace('doi = "10.71929/rubin/2570308"\n', "")
    )

    document = yaml.safe_load(
        TechnoteCffService.from_technote_toml(toml_path).render()
    )

    assert "doi" not in document
    assert str(document["date-released"]) == "2026-08-24"


@pytest.mark.parametrize(
    "source",
    [
        pytest.param(FULL_TOML, id="dated"),
        pytest.param(CREATED_ONLY_TOML, id="undated"),
    ],
)
def test_the_generated_file_is_valid_cff(tmp_path: Path, source: str) -> None:
    """The generated file satisfies CFF 1.2.0 whether or not the technote
    states a release date.

    CFF requires ``date-released`` at neither level, so omitting the date a
    technote never declared costs the file nothing.
    """
    toml_path = tmp_path / "technote.toml"
    toml_path.write_text(source)

    document = yaml.safe_load(
        TechnoteCffService.from_technote_toml(toml_path).render()
    )

    assert_valid_cff(document)


def test_the_cff_assertion_catches_a_missing_required_key() -> None:
    """The validity assertion has teeth: a file missing a key CFF 1.2.0
    requires fails it, rather than passing everything handed to it.
    """
    document = {
        "cff-version": "1.2.0",
        "title": "A repository",
        "type": "software",
        "authors": [{"family-names": "Sick"}],
    }

    with pytest.raises(AssertionError):
        assert_valid_cff(document)


def test_the_documented_example_is_what_the_generator_writes(
    tmp_path: Path,
) -> None:
    """The guide's example CITATION.cff is generated output rather than a
    hand-written approximation of it, so a change to the generated shape
    cannot leave the page describing a file Documenteer no longer writes.
    """
    toml_path = tmp_path / "technote.toml"
    toml_path.write_text(FULL_TOML)

    rendered = TechnoteCffService.from_technote_toml(toml_path).render()

    assert read_documented_cff() == rendered


def test_a_date_updated_that_is_not_a_date_is_reported(
    tmp_path: Path,
) -> None:
    """A ``date_updated`` written as text TOML does not read as a date is
    named in the diagnostic, rather than reaching the citation as one.
    """
    toml_path = tmp_path / "technote.toml"
    toml_path.write_text(
        FULL_TOML.replace("date_updated = 2026-08-24", 'date_updated = "soon"')
    )

    with pytest.raises(TechnoteCffError) as exc_info:
        TechnoteCffService.from_technote_toml(toml_path)

    assert "declares a date_updated that is not a date: soon" in str(
        exc_info.value
    )
