"""Tests for the TechnoteLintService class."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import pytest_responses  # noqa: F401
import requests
from responses import RequestsMock, matchers

from documenteer.services.technotecff import TechnoteCffService
from documenteer.services.technotelint import (
    CHECKS,
    Check,
    IgnoredRule,
    IgnoreSource,
    LintContext,
    Severity,
    TechnoteLintService,
    check_abstract,
    check_requirements,
    rule_url,
)
from documenteer.storage.authordb import AuthorDb

AUTHOR_JSON = """
{
    "affiliations": [],
    "family_name": "Sick",
    "given_name": "Jonathan",
    "internal_id": "sickj",
    "notes": [],
    "orcid": "https://orcid.org/0000-0003-3001-676X"
}
"""


def _search_result(
    internal_id: str,
    given_name: str,
    family_name: str,
    score: float,
    orcid: str | None = None,
) -> dict[str, object]:
    """Build one entry of an Ook author-search response body."""
    return {
        "affiliations": [],
        "family_name": family_name,
        "given_name": given_name,
        "internal_id": internal_id,
        "notes": [],
        "orcid": orcid,
        "score": score,
    }


def _author_record(
    internal_id: str,
    given_name: str,
    family_name: str,
    orcid: str | None = None,
) -> dict[str, object]:
    """Build one entry of an Ook ORCID-lookup response body.

    Unlike a name-search result, an ORCID lookup's records carry no score.
    """
    return {
        "affiliations": [],
        "family_name": family_name,
        "given_name": given_name,
        "internal_id": internal_id,
        "notes": [],
        "orcid": orcid,
    }


def _mock_orcid_lookup(
    responses: RequestsMock,
    orcid: str,
    records: list[dict[str, object]],
) -> None:
    """Register Ook's exact ORCID lookup, which the linter tries first."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors",
        body=json.dumps(records),
        content_type="application/json",
        status=200,
        match=[matchers.query_param_matcher({"orcid": orcid})],
    )


def _mock_name_search(
    responses: RequestsMock, results: list[dict[str, object]]
) -> None:
    """Register Ook's fuzzy name search, the linter's fallback."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors",
        body=json.dumps(results),
        content_type="application/json",
        status=200,
        match=[
            matchers.query_param_matcher({"limit": "10"}, strict_match=False)
        ],
    )


def _write_technote(tmp_path: Path, toml_content: str) -> LintContext:
    """Write a technote.toml into ``tmp_path`` and build a context.

    Also writes an ``index.rst`` with a well-formed abstract and a sane
    ``requirements.txt`` so the content-group abstract check (TN201/TN202)
    and the structural requirements check (TN002/TN003) stay silent and
    these metadata-focused tests observe only author/schema findings.
    """
    (tmp_path / "technote.toml").write_text(toml_content)
    (tmp_path / "index.rst").write_text(
        "#####\nTitle\n#####\n\n.. abstract::\n\n   An abstract.\n"
    )
    (tmp_path / "requirements.txt").write_text("documenteer[technote]\n")
    return LintContext.from_dir(tmp_path, AuthorDb())


def test_valid_authors_pass(tmp_path: Path, responses: RequestsMock) -> None:
    """A schema-valid technote with a resolvable author has no findings."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/sickj",
        body=AUTHOR_JSON,
        content_type="application/json",
        status=200,
    )
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "Jonathan"
name.family = "Sick"
internal_id = "sickj"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert findings == []


def test_missing_internal_id(tmp_path: Path) -> None:
    """Each author lacking an internal_id yields one TN101 error."""
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "Jonathan"
name.family = "Sick"

[[technote.authors]]
name.given = "Frossie"
name.family = "Economou"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN101", "TN101"]
    assert all(f.severity is Severity.error for f in findings)


def test_missing_internal_id_suggests_orcid_match(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A TN101 author whose ORCID is in the DB gets a suggested ID."""
    _mock_orcid_lookup(
        responses,
        "0009-0008-9216-7516",
        [
            _author_record(
                "alsayyady",
                "Yusra",
                "AlSayyad",
                orcid="https://orcid.org/0009-0008-9216-7516",
            )
        ],
    )
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "Yusra"
name.family = "AlSayyad"
orcid = "https://orcid.org/0009-0008-9216-7516"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN101"]
    assert findings[0].message == (
        "Author Yusra AlSayyad is missing an internal_id. Did you mean "
        "'alsayyady' (matched by ORCID)? Run 'documenteer technote "
        "sync-authors' to add it."
    )


def test_internal_id_not_found(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """An internal_id absent from the author DB (404) yields TN102."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/nobody",
        body="Not found",
        status=404,
    )
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "No"
name.family = "Body"
internal_id = "nobody"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN102"]
    assert findings[0].severity is Severity.error


def test_unknown_internal_id_suggests_name_match(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A TN102 author with one near-exact name match gets a suggested ID."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/lynnej",
        body="Not found",
        status=404,
    )
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors",
        body=json.dumps(
            [
                _search_result("jonesrl", "R. Lynne", "Jones", 90.0),
                _search_result("jonesd", "Derek", "Jones", 70.0),
                _search_result("jonesrwl", "Roger", "Jones", 70.0),
            ]
        ),
        content_type="application/json",
        status=200,
    )
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "Lynne"
name.family = "Jones"
internal_id = "lynnej"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN102"]
    assert findings[0].message == (
        "Author Lynne Jones has internal_id 'lynnej', which is not in the "
        "author database. Did you mean 'jonesrl' (R. Lynne Jones, matched "
        "by name)?"
    )


def test_ambiguous_name_match_keeps_plain_message(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """Several equally-good name matches suggest nothing."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors",
        body=json.dumps(
            [
                _search_result("jonesd", "Derek", "Jones", 90.0),
                _search_result("jonesrl", "R. Lynne", "Jones", 90.0),
            ]
        ),
        content_type="application/json",
        status=200,
    )
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "L."
name.family = "Jones"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN101"]
    assert findings[0].message == "Author L. Jones is missing an internal_id."


def test_weak_name_match_keeps_plain_message(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A search with no near-exact result suggests nothing."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors",
        body=json.dumps([_search_result("jonesd", "Derek", "Jones", 45.0)]),
        content_type="application/json",
        status=200,
    )
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "Nemo"
name.family = "Nobody"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN101"]
    assert (
        findings[0].message == "Author Nemo Nobody is missing an internal_id."
    )


def test_conflicting_orcid_keeps_plain_message(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A name match whose ORCID differs is a different person, so no hint."""
    _mock_orcid_lookup(responses, "0000-0003-3001-676X", [])
    _mock_name_search(
        responses,
        [
            _search_result(
                "jonesd",
                "Derek",
                "Jones",
                90.0,
                orcid="https://orcid.org/0000-0001-5916-0031",
            )
        ],
    )
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "Derek"
name.family = "Jones"
orcid = "https://orcid.org/0000-0003-3001-676X"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN101"]
    assert (
        findings[0].message == "Author Derek Jones is missing an internal_id."
    )


def test_suggestion_lookup_failure_keeps_plain_message(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A failed suggestion lookup leaves the finding as it was."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors",
        body="Internal server error",
        status=500,
    )
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "Jonathan"
name.family = "Sick"
orcid = "https://orcid.org/0000-0003-3001-676X"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN101"]
    assert findings[0].severity is Severity.error
    assert (
        findings[0].message
        == "Author Jonathan Sick is missing an internal_id."
    )


def test_authordb_unreachable(tmp_path: Path, responses: RequestsMock) -> None:
    """An unreachable author DB yields a TN103 warning, not an error."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/sickj",
        body=requests.ConnectionError("connection refused"),
    )
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "Jonathan"
name.family = "Sick"
internal_id = "sickj"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN103"]
    assert findings[0].severity is Severity.warning


def test_invalid_schema_skips_author_checks(tmp_path: Path) -> None:
    """A schema failure yields TN001 and skips the model-dependent checks."""
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "Jonathan"

[[technote.authors]]
name.given = "Frossie"
name.family = "Economou"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    # The second author has no internal_id, but TN101 needs the parsed model,
    # so only the schema finding is reported.
    assert [f.code for f in findings] == ["TN001"]
    assert findings[0].severity is Severity.error


def test_invalid_schema_still_runs_toml_independent_checks(
    tmp_path: Path,
) -> None:
    """A schema failure no longer suppresses the TN002/TN2xx checks."""
    (tmp_path / "technote.toml").write_text(
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "Jonathan"
"""
    )
    (tmp_path / "index.rst").write_text(
        "#####\nTitle\n#####\n\nIntroduction\n============\n\nBody.\n"
    )
    (tmp_path / "requirements.txt").write_text("sphinx==8.1.0\n")
    context = LintContext.from_dir(tmp_path, AuthorDb())
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN001", "TN201", "TN002", "TN003"]


def test_legacy_single_string_author_name_reports_tn001(
    tmp_path: Path,
) -> None:
    """The removed ``name = {name = "..."}`` form gets a targeted message."""
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name = { name = "Jonathan Sick" }
internal_id = "sickj"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN001"]
    message = findings[0].message
    assert 'name = { name = "Full Name" }' in message
    assert "technote 0.5" in message
    assert 'name = { given = "Given", family = "Family" }' in message
    assert "documenteer technote migrate" in message
    # The pydantic detail is retained for anyone debugging the schema error.
    assert "technote.authors.0.name" in message


def test_legacy_split_name_keys_report_tn001(tmp_path: Path) -> None:
    """The renamed ``given_names``/``family_names`` keys are called out."""
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name = { given_names = "Jonathan", family_names = "Sick" }
internal_id = "sickj"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN001"]
    message = findings[0].message
    assert 'name = { given_names = "...", family_names = "..." }' in message
    assert "renamed in November 2023" in message
    assert 'name = { given = "Given", family = "Family" }' in message
    assert "documenteer technote migrate" in message


def test_non_author_schema_error_has_no_legacy_message(
    tmp_path: Path,
) -> None:
    """A schema error unrelated to author names keeps the plain message."""
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"
canonical_url = "not a url"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN001"]
    message = findings[0].message
    assert "documenteer technote migrate" not in message
    assert "canonical_url" in message


def test_other_author_schema_error_has_no_legacy_message(
    tmp_path: Path,
) -> None:
    """An author with a non-legacy schema error keeps the plain message."""
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name = { given = "Jonathan", family = "Sick" }
orcid = "not-an-orcid"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN001"]
    assert "documenteer technote migrate" not in findings[0].message


def test_missing_toml_reports_tn004(tmp_path: Path) -> None:
    """A directory with no technote.toml yields a single TN004 error."""
    context = LintContext.from_dir(tmp_path, AuthorDb())
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN004"]
    assert findings[0].severity is Severity.error


def test_malformed_toml_reports_tn005(tmp_path: Path) -> None:
    """A syntactically broken technote.toml yields a TN005 error.

    The TOML-independent checks still run, so the missing abstract and
    requirements.txt are reported in the same pass.
    """
    (tmp_path / "technote.toml").write_text("[technote\nid = ")
    (tmp_path / "index.rst").write_text(
        "#####\nTitle\n#####\n\nIntroduction\n============\n\nBody.\n"
    )
    context = LintContext.from_dir(tmp_path, AuthorDb())
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN005", "TN201", "TN002"]
    assert findings[0].severity is Severity.error


def test_author_record_malformed_reports_tn102(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A 200 response with an unparseable author body yields a TN102 error."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/sickj",
        body="{ not valid json",
        content_type="application/json",
        status=200,
    )
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "Jonathan"
name.family = "Sick"
internal_id = "sickj"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN102"]
    assert findings[0].severity is Severity.error
    assert "malformed" in findings[0].message


def test_malformed_doi_reports_schema_error(tmp_path: Path) -> None:
    """A [technote] doi that is not a DOI is a schema-conformance error.

    technote 0.10.0 validates and normalizes ``[technote] doi`` inside
    ``TechnoteToml.parse_toml``, so a malformed DOI raises
    `pydantic.ValidationError` before any rule sees a parsed model and the
    linter reports it as TN001. That is why the DOI has no rule of its own:
    the TN001 finding names both the ``technote.doi`` field and the offending
    value, so it stands alone as the report.
    """
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"
doi = "10.71929"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN001"]
    assert findings[0].severity is Severity.error
    assert "technote.doi" in findings[0].message
    assert "10.71929" in findings[0].message


@pytest.mark.parametrize(
    "doi",
    [
        "10.71929/rubin/2570308",
        "https://doi.org/10.71929/rubin/2570308",
        "doi:10.71929/rubin/2570308",
        "doi: 10.71929/rubin/2570308",
    ],
)
def test_well_formed_doi_passes(
    tmp_path: Path, responses: RequestsMock, doi: str
) -> None:
    """Every spelling the DOI normalizer accepts is silent."""
    # A well-formed DOI reaches TN105's DataCite cross-check, so the
    # registered metadata has to be answered here: without this
    # registration the request is refused, TN105 degrades down its
    # DataCite-unreachable path, and this test would pass for that reason
    # rather than for the spelling it is about. One registration serves
    # every parametrization because each spelling normalizes to this same
    # API URL, and the fixture's assert_all_requests_are_fired makes that
    # normalization an assertion.
    responses.get(
        DATACITE_URL,
        body=_datacite_body(),
        content_type="application/vnd.api+json",
        status=200,
    )
    context = _write_technote(
        tmp_path,
        f"""
[technote]
id = "SQR-000"
doi = "{doi}"
""",
    )
    service = TechnoteLintService(context)
    assert service.lint() == []


def test_absent_doi_passes(tmp_path: Path) -> None:
    """A technote that declares no DOI is not flagged."""
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"
""",
    )
    service = TechnoteLintService(context)
    assert service.lint() == []


def test_empty_doi_passes(tmp_path: Path) -> None:
    """An empty ``doi`` placeholder is an unset DOI, not a finding.

    technote documents ``doi = ""`` as a placeholder that existing
    ``technote.toml`` files may keep, and normalizes it to `None` when the
    file is parsed. The linter has to agree: a technote awaiting its first
    DOI must lint clean.
    """
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"
doi = ""
""",
    )
    service = TechnoteLintService(context)
    assert service.lint() == []


CITABLE_HEADER = """
[technote]
id = "SQR-000"
title = "The technote"
doi = "10.71929/rubin/2570308"

[technote.organization]
name = "Vera C. Rubin Observatory"
"""
"""The non-author half of a technote.toml with a DOI and a title."""


def _author_block(
    given: str, family: str, internal_id: str, orcid: str | None = None
) -> str:
    """Write one ``[[technote.authors]]`` block."""
    block = (
        "\n[[technote.authors]]\n"
        f'name.given = "{given}"\n'
        f'name.family = "{family}"\n'
        f'internal_id = "{internal_id}"\n'
    )
    if orcid is not None:
        block += f'orcid = "{orcid}"\n'
    return block


CITABLE_TOML = CITABLE_HEADER + _author_block("Jonathan", "Sick", "sickj")
"""A technote.toml with enough metadata to compose a CITATION.cff.

Its one author declares an ``internal_id``, so the author checks (TN1xx)
resolve it against the mocked author database rather than reporting.
"""


def test_stale_citation_cff_reports_tn106(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A CITATION.cff that differs from technote.toml yields a TN106 error."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/sickj",
        body=AUTHOR_JSON,
        content_type="application/json",
        status=200,
    )
    context = _write_technote(tmp_path, CITABLE_TOML)
    (tmp_path / "CITATION.cff").write_text(
        "cff-version: 1.2.0\ntitle: An older title\n"
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN106"]
    assert findings[0].severity is Severity.error
    assert "documenteer technote sync-cff" in findings[0].message


def test_current_citation_cff_passes(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A CITATION.cff that sync-cff would regenerate identically is silent."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/sickj",
        body=AUTHOR_JSON,
        content_type="application/json",
        status=200,
    )
    context = _write_technote(tmp_path, CITABLE_TOML)
    generator = TechnoteCffService.from_technote_toml(
        tmp_path / "technote.toml"
    )
    (tmp_path / "CITATION.cff").write_text(generator.render())
    service = TechnoteLintService(context)
    assert service.lint() == []


def test_absent_citation_cff_passes(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A repository that has not adopted CITATION.cff is silent."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/sickj",
        body=AUTHOR_JSON,
        content_type="application/json",
        status=200,
    )
    context = _write_technote(tmp_path, CITABLE_TOML)
    assert not (tmp_path / "CITATION.cff").exists()
    service = TechnoteLintService(context)
    assert service.lint() == []


def test_uncitable_technote_toml_skips_tn106(tmp_path: Path) -> None:
    """Metadata that cannot compose a citation reports no staleness.

    A technote.toml that names the technote neither by title nor by id
    stops the CITATION.cff generator, so there is nothing to compare the
    stale-looking file against and TN106 is silent. (The DOI is no longer a
    way to reach this path: technote 0.10.0 validates ``[technote] doi``
    inside ``parse_toml``, so a malformed one fails schema conformance long
    before the CITATION.cff comparison — see #439.)
    """
    context = _write_technote(
        tmp_path,
        """
[technote]
""",
    )
    (tmp_path / "CITATION.cff").write_text("cff-version: 1.2.0\n")
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == []


DOI = "10.71929/rubin/2570308"
"""The DOI the DataCite cross-check tests declare in technote.toml."""

DATACITE_URL = f"https://api.datacite.org/dois/{DOI}"
"""The API URL TN105 reads that DOI's registered metadata from."""


def _creator(
    *,
    given: str | None = None,
    family: str | None = None,
    name: str | None = None,
    name_type: str = "Personal",
    orcid: str | None = None,
) -> dict[str, object]:
    """Build one ``creators`` entry, shaped as Rubin's minter registers it.

    ``orcid`` is deposited verbatim as a ``nameIdentifier``, so a test can
    register either a bare identifier or an ``orcid.org`` URL.
    """
    entry: dict[str, object] = {"nameType": name_type}
    if given is not None:
        entry["givenName"] = given
    if family is not None:
        entry["familyName"] = family
    if name is not None:
        entry["name"] = name
    elif given is not None and family is not None:
        entry["name"] = f"{family}, {given}"
    entry["nameIdentifiers"] = (
        []
        if orcid is None
        else [{"nameIdentifier": orcid, "nameIdentifierScheme": "ORCID"}]
    )
    return entry


def _datacite_body(
    *,
    title: str = "The technote",
    creators: tuple[dict[str, object], ...] = (
        {
            "nameType": "Personal",
            "givenName": "Jonathan",
            "familyName": "Sick",
            "name": "Sick, Jonathan",
        },
    ),
) -> str:
    """Build a DataCite ``/dois/{id}`` response body for `DOI`."""
    return json.dumps(
        {
            "data": {
                "id": DOI,
                "type": "dois",
                "attributes": {
                    "doi": DOI,
                    "titles": [{"title": title}],
                    "creators": list(creators),
                    "publisher": "Vera C. Rubin Observatory",
                    "publicationYear": 2026,
                },
            }
        }
    )


def _mock_author(responses: RequestsMock) -> None:
    """Mock the author-database lookup CITABLE_TOML's one author needs."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/sickj",
        body=AUTHOR_JSON,
        content_type="application/json",
        status=200,
    )


def _mock_second_author(responses: RequestsMock) -> None:
    """Mock the lookup TWO_AUTHOR_TOML's second author needs."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/alsayyady",
        body=json.dumps(
            _author_record(
                "alsayyady",
                "Yusra",
                "AlSayyad",
                "https://orcid.org/0000-0002-1793-3689",
            )
        ),
        content_type="application/json",
        status=200,
    )


TWO_AUTHOR_TOML = CITABLE_TOML + _author_block(
    "Yusra", "AlSayyad", "alsayyady"
)
"""CITABLE_TOML with a second author, for the author-set comparison."""

SICK = _creator(given="Jonathan", family="Sick")
"""The creator CITABLE_TOML's author is registered as."""

ALSAYYAD = _creator(given="Yusra", family="AlSayyad")
"""The creator TWO_AUTHOR_TOML's second author is registered as."""


def test_datacite_title_drift_reports_tn105(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A registered title that differs from technote.toml is a TN105
    warning.
    """
    _mock_author(responses)
    responses.get(
        DATACITE_URL,
        body=_datacite_body(title="An older title"),
        content_type="application/vnd.api+json",
        status=200,
    )
    context = _write_technote(tmp_path, CITABLE_TOML)
    findings = TechnoteLintService(context).lint()
    assert [f.code for f in findings] == ["TN105"]
    assert findings[0].severity is Severity.warning
    assert "title" in findings[0].message
    assert "An older title" in findings[0].message
    assert "The technote" in findings[0].message
    assert DATACITE_URL in findings[0].message


def test_datacite_author_drift_reports_tn105(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A registered author list that differs from technote.toml is a TN105
    warning.
    """
    _mock_author(responses)
    responses.get(
        DATACITE_URL,
        body=_datacite_body(creators=(ALSAYYAD,)),
        content_type="application/vnd.api+json",
        status=200,
    )
    context = _write_technote(tmp_path, CITABLE_TOML)
    findings = TechnoteLintService(context).lint()
    assert [f.code for f in findings] == ["TN105"]
    assert "authors" in findings[0].message
    assert "AlSayyad, Yusra" in findings[0].message
    assert "Sick, Jonathan" in findings[0].message
    assert DATACITE_URL in findings[0].message


def test_datacite_drift_names_every_differing_field(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """Title and author drift are reported together, in one finding."""
    _mock_author(responses)
    responses.get(
        DATACITE_URL,
        body=_datacite_body(title="An older title", creators=(ALSAYYAD,)),
        content_type="application/vnd.api+json",
        status=200,
    )
    context = _write_technote(tmp_path, CITABLE_TOML)
    findings = TechnoteLintService(context).lint()
    assert [f.code for f in findings] == ["TN105"]
    assert "title" in findings[0].message
    assert "authors" in findings[0].message


def test_matching_datacite_metadata_passes(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """Registered metadata that agrees with technote.toml is silent."""
    _mock_author(responses)
    responses.get(
        DATACITE_URL,
        body=_datacite_body(),
        content_type="application/vnd.api+json",
        status=200,
    )
    context = _write_technote(tmp_path, CITABLE_TOML)
    assert TechnoteLintService(context).lint() == []


@pytest.mark.parametrize(
    "title",
    [
        "The technote",
        "the TECHNOTE",
        "The  technote\n",
    ],
)
def test_title_comparison_tolerates_case_and_whitespace(
    tmp_path: Path, responses: RequestsMock, title: str
) -> None:
    """Case and whitespace differences in a title are not drift."""
    _mock_author(responses)
    responses.get(
        DATACITE_URL,
        body=_datacite_body(title=title),
        content_type="application/vnd.api+json",
        status=200,
    )
    context = _write_technote(tmp_path, CITABLE_TOML)
    assert TechnoteLintService(context).lint() == []


@pytest.mark.parametrize(
    "creators",
    [
        (SICK, ALSAYYAD),
        # The order DataCite lists creators in is not metadata drift.
        (ALSAYYAD, SICK),
        # Neither is how either side spells a name's case.
        (
            _creator(given="JONATHAN", family="sick"),
            _creator(given="Yusra", family="Alsayyad"),
        ),
    ],
)
def test_author_comparison_tolerates_order_and_case(
    tmp_path: Path,
    responses: RequestsMock,
    creators: tuple[dict[str, object], ...],
) -> None:
    """Authors are paired regardless of order, ignoring case."""
    _mock_author(responses)
    _mock_second_author(responses)
    responses.get(
        DATACITE_URL,
        body=_datacite_body(creators=creators),
        content_type="application/vnd.api+json",
        status=200,
    )
    context = _write_technote(tmp_path, TWO_AUTHOR_TOML)
    assert TechnoteLintService(context).lint() == []


@pytest.mark.parametrize(
    "registered_family",
    ["Ibáñez", "Ibanez", "IBÁÑEZ"],
)
def test_family_name_comparison_folds_accents(
    tmp_path: Path, responses: RequestsMock, registered_family: str
) -> None:
    """A family name registered without its accents is the same name."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/ibanezj",
        body=json.dumps(_author_record("ibanezj", "José", "Ibáñez")),
        content_type="application/json",
        status=200,
    )
    responses.get(
        DATACITE_URL,
        body=_datacite_body(
            creators=(_creator(given="José", family=registered_family),)
        ),
        content_type="application/vnd.api+json",
        status=200,
    )
    context = _write_technote(
        tmp_path,
        CITABLE_HEADER + _author_block("José", "Ibáñez", "ibanezj"),
    )
    assert TechnoteLintService(context).lint() == []


@pytest.mark.parametrize(
    ("registered_given", "declared_given"),
    [
        # A middle initial the record carries and technote.toml does not.
        ("James F.", "James"),
        # A first initial technote.toml drops in favour of the name used.
        ("R. Lynne", "Lynne"),
        # An initial standing in for the whole given name.
        ("J.", "Jonathan"),
    ],
)
def test_given_name_comparison_tolerates_initials(
    tmp_path: Path,
    responses: RequestsMock,
    registered_given: str,
    declared_given: str,
) -> None:
    """A given name abbreviated on either side is the same author."""
    _mock_author(responses)
    responses.get(
        DATACITE_URL,
        body=_datacite_body(
            creators=(_creator(given=registered_given, family="Sick"),)
        ),
        content_type="application/vnd.api+json",
        status=200,
    )
    context = _write_technote(
        tmp_path,
        CITABLE_HEADER + _author_block(declared_given, "Sick", "sickj"),
    )
    assert TechnoteLintService(context).lint() == []


def test_differing_given_name_reports_tn105(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A given name that shares a family name but not an initial is drift."""
    _mock_author(responses)
    responses.get(
        DATACITE_URL,
        body=_datacite_body(creators=(_creator(given="John", family="Sick"),)),
        content_type="application/vnd.api+json",
        status=200,
    )
    context = _write_technote(
        tmp_path, CITABLE_HEADER + _author_block("James", "Sick", "sickj")
    )
    findings = TechnoteLintService(context).lint()
    assert [f.code for f in findings] == ["TN105"]
    assert "Sick, John" in findings[0].message
    assert "Sick, James" in findings[0].message


def test_transposed_name_reports_tn105(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A given and family name registered the wrong way round is drift.

    This is the drift the old token-set comparison silently accepted: sorting
    a name's tokens makes a transposition compare equal to the original.
    """
    _mock_author(responses)
    responses.get(
        DATACITE_URL,
        body=_datacite_body(
            creators=(_creator(given="Sick", family="Jonathan"),)
        ),
        content_type="application/vnd.api+json",
        status=200,
    )
    context = _write_technote(tmp_path, CITABLE_TOML)
    findings = TechnoteLintService(context).lint()
    assert [f.code for f in findings] == ["TN105"]
    assert "Jonathan, Sick" in findings[0].message
    assert "Sick, Jonathan" in findings[0].message


def test_added_author_reports_tn105(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """An author the record registers and technote.toml does not is named."""
    _mock_author(responses)
    responses.get(
        DATACITE_URL,
        body=_datacite_body(creators=(SICK, ALSAYYAD)),
        content_type="application/vnd.api+json",
        status=200,
    )
    context = _write_technote(tmp_path, CITABLE_TOML)
    findings = TechnoteLintService(context).lint()
    assert [f.code for f in findings] == ["TN105"]
    assert "AlSayyad, Yusra" in findings[0].message
    assert "Sick, Jonathan" not in findings[0].message
    assert DATACITE_URL in findings[0].message


def test_dropped_author_reports_tn105(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """An author technote.toml declares and the record omits is named."""
    _mock_author(responses)
    _mock_second_author(responses)
    responses.get(
        DATACITE_URL,
        body=_datacite_body(creators=(SICK,)),
        content_type="application/vnd.api+json",
        status=200,
    )
    context = _write_technote(tmp_path, TWO_AUTHOR_TOML)
    findings = TechnoteLintService(context).lint()
    assert [f.code for f in findings] == ["TN105"]
    assert "AlSayyad, Yusra" in findings[0].message
    assert DATACITE_URL in findings[0].message


ORCID = "0000-0003-3001-676X"
"""The ORCID CITABLE_TOML's author holds."""


def test_orcid_match_settles_a_differing_name(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """An author paired by ORCID is not reported for spelling their name
    differently.
    """
    _mock_author(responses)
    responses.get(
        DATACITE_URL,
        body=_datacite_body(
            creators=(
                _creator(
                    given="Jonathan",
                    family="Sick",
                    orcid=f"https://orcid.org/{ORCID}",
                ),
            )
        ),
        content_type="application/vnd.api+json",
        status=200,
    )
    context = _write_technote(
        tmp_path,
        CITABLE_HEADER
        + _author_block("Jon", "Sicke", "sickj", f"https://orcid.org/{ORCID}"),
    )
    assert TechnoteLintService(context).lint() == []


def test_orcid_match_normalizes_both_spellings(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A bare ORCID and an orcid.org URL identify the same author."""
    _mock_author(responses)
    responses.get(
        DATACITE_URL,
        body=_datacite_body(
            creators=(
                _creator(given="J.", family="Sicke", orcid=ORCID.lower()),
            )
        ),
        content_type="application/vnd.api+json",
        status=200,
    )
    context = _write_technote(
        tmp_path,
        CITABLE_HEADER + _author_block("Jonathan", "Sick", "sickj", ORCID),
    )
    assert TechnoteLintService(context).lint() == []


def test_author_with_no_registered_orcid_falls_back_to_the_name(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """An ORCID only one side declares leaves the names to decide."""
    _mock_author(responses)
    responses.get(
        DATACITE_URL,
        body=_datacite_body(creators=(SICK,)),
        content_type="application/vnd.api+json",
        status=200,
    )
    context = _write_technote(
        tmp_path,
        CITABLE_HEADER + _author_block("Jonathan", "Sick", "sickj", ORCID),
    )
    assert TechnoteLintService(context).lint() == []


OTHER_ORCID = "0000-0002-1793-3689"
"""An ORCID belonging to somebody other than CITABLE_TOML's author."""


def test_conflicting_orcids_are_reported(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A creator that names the declared author under a different ORCID is
    reported, rather than paired over by the name pass.

    The two sides agree on the name, so the name pass pairs them — but one of
    the two ORCIDs identifies somebody else, and an ORCID is the claim this
    rule trusts above any spelling of a name.
    """
    _mock_author(responses)
    responses.get(
        DATACITE_URL,
        body=_datacite_body(
            creators=(
                _creator(given="Jonathan", family="Sick", orcid=OTHER_ORCID),
            )
        ),
        content_type="application/vnd.api+json",
        status=200,
    )
    context = _write_technote(
        tmp_path,
        CITABLE_HEADER + _author_block("Jonathan", "Sick", "sickj", ORCID),
    )

    findings = TechnoteLintService(context).lint()

    assert [f.code for f in findings] == ["TN105"]
    assert (
        "the ORCID registered for 'Sick, Jonathan' is "
        f"https://orcid.org/{OTHER_ORCID}, but technote.toml declares "
        f"https://orcid.org/{ORCID}"
    ) in findings[0].message


def test_committee_creator_matches_its_declared_author(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A creator registered as a family name alone is compared on it.

    This is a real record under the ``10.71929`` prefix: Rubin's minter
    registers a committee as a ``Personal`` creator with only a
    ``familyName``, which leaves a literal ``null`` in the formatted ``name``
    it composes. Reading the formatted name would report drift over that
    artifact; the decomposed family name has no such defect.
    """
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/scoc",
        body=json.dumps(
            _author_record(
                "scoc", "", "Rubin's Survey Cadence Optimization Committee"
            )
        ),
        content_type="application/json",
        status=200,
    )
    responses.get(
        DATACITE_URL,
        body=_datacite_body(
            creators=(
                _creator(
                    family="Rubin's Survey Cadence Optimization Committee",
                    name="Rubin's Survey Cadence Optimization Committee, null",
                ),
            )
        ),
        content_type="application/vnd.api+json",
        status=200,
    )
    context = _write_technote(
        tmp_path,
        CITABLE_HEADER
        + _author_block(
            "", "Rubin's Survey Cadence Optimization Committee", "scoc"
        ),
    )
    assert TechnoteLintService(context).lint() == []


def test_organizational_creator_matches_its_declared_author(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """An organizational creator is compared on its formatted name."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/rubinobs",
        body=json.dumps(
            _author_record("rubinobs", "", "Vera C. Rubin Observatory")
        ),
        content_type="application/json",
        status=200,
    )
    responses.get(
        DATACITE_URL,
        body=_datacite_body(
            creators=(
                _creator(
                    name="Vera C. Rubin Observatory",
                    name_type="Organizational",
                ),
            )
        ),
        content_type="application/vnd.api+json",
        status=200,
    )
    context = _write_technote(
        tmp_path,
        CITABLE_HEADER
        + _author_block("", "Vera C. Rubin Observatory", "rubinobs"),
    )
    assert TechnoteLintService(context).lint() == []


def test_unregistered_doi_skips_tn105(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A DOI DataCite does not know is silent, not drift."""
    _mock_author(responses)
    responses.get(
        DATACITE_URL,
        body='{"errors":[{"status":"404"}]}',
        content_type="application/vnd.api+json",
        status=404,
    )
    context = _write_technote(tmp_path, CITABLE_TOML)
    assert TechnoteLintService(context).lint() == []


@pytest.mark.parametrize(
    "failure",
    [
        requests.ConnectionError("no route to host"),
        requests.ReadTimeout("too slow"),
    ],
)
def test_unreachable_datacite_skips_tn105(
    tmp_path: Path, responses: RequestsMock, failure: Exception
) -> None:
    """A technote author with no network gets a clean lint run."""
    _mock_author(responses)
    responses.get(DATACITE_URL, body=failure)
    context = _write_technote(tmp_path, CITABLE_TOML)
    assert TechnoteLintService(context).lint() == []


def test_datacite_server_error_skips_tn105(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A DataCite outage is silent rather than reported as drift."""
    _mock_author(responses)
    responses.get(DATACITE_URL, body="Service unavailable", status=503)
    context = _write_technote(tmp_path, CITABLE_TOML)
    assert TechnoteLintService(context).lint() == []


def test_unreadable_datacite_response_skips_tn105(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A response that is not a DOI record leaves the metadata unknown."""
    _mock_author(responses)
    responses.get(
        DATACITE_URL,
        body='{"meta": {}}',
        content_type="application/vnd.api+json",
        status=200,
    )
    context = _write_technote(tmp_path, CITABLE_TOML)
    assert TechnoteLintService(context).lint() == []


def test_malformed_doi_skips_datacite(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A DOI that is not a DOI asks DataCite nothing.

    technote 0.10.0 validates ``[technote] doi`` inside ``parse_toml``, so
    the malformed value is a schema-conformance failure (TN001) and TN105
    never gets a parsed model to cross-check.
    """
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"
title = "The technote"
doi = "10.71929"
""",
    )
    findings = TechnoteLintService(context).lint()
    assert [f.code for f in findings] == ["TN001"]
    assert len(responses.calls) == 0


def test_absent_doi_skips_datacite(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A technote with no DOI has nothing to cross-check."""
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"
title = "The technote"
""",
    )
    assert TechnoteLintService(context).lint() == []
    assert len(responses.calls) == 0


def test_untitled_technote_skips_the_title_comparison(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A technote.toml that declares no title cannot disagree about one."""
    responses.get(
        DATACITE_URL,
        body=_datacite_body(title="A registered title", creators=()),
        content_type="application/vnd.api+json",
        status=200,
    )
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"
doi = "10.71929/rubin/2570308"
""",
    )
    assert TechnoteLintService(context).lint() == []


def test_authorless_datacite_record_skips_the_author_comparison(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A record that lists no creators is not read as an empty author set."""
    _mock_author(responses)
    responses.get(
        DATACITE_URL,
        body=_datacite_body(creators=()),
        content_type="application/vnd.api+json",
        status=200,
    )
    context = _write_technote(tmp_path, CITABLE_TOML)
    assert TechnoteLintService(context).lint() == []


def _write_non_sphinx_technote(tmp_path: Path, toml_content: str) -> None:
    """Write a non-Sphinx technote: a technote.toml, no index, no conf.py.

    Mirrors a technote-series repository that is published through the shared
    technote CI with a custom build command (for example an org-mode deck),
    including the deliberately empty ``requirements.txt`` such a repository
    carries.
    """
    (tmp_path / "technote.toml").write_text(toml_content)
    (tmp_path / "requirements.txt").write_text("")


def test_non_sphinx_technote_passes(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A healthy non-Sphinx technote reports nothing, so the run exits 0."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/sickj",
        body=AUTHOR_JSON,
        content_type="application/json",
        status=200,
    )
    _write_non_sphinx_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "Jonathan"
name.family = "Sick"
internal_id = "sickj"
""",
    )
    context = LintContext.from_dir(tmp_path, AuthorDb())
    service = TechnoteLintService(context)
    assert service.lint() == []


def test_non_sphinx_technote_reports_schema_errors(tmp_path: Path) -> None:
    """A non-Sphinx technote's technote.toml is still schema-checked."""
    _write_non_sphinx_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"
canonical_url = "not a url"
""",
    )
    context = LintContext.from_dir(tmp_path, AuthorDb())
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN001"]


def test_non_sphinx_technote_runs_author_checks(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A non-Sphinx technote's authors are still resolved against the DB."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/nobody",
        body="Not found",
        status=404,
    )
    _write_non_sphinx_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "No"
name.family = "Body"
internal_id = "nobody"
""",
    )
    context = LintContext.from_dir(tmp_path, AuthorDb())
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN102"]


def _context_with_content(
    tmp_path: Path, filename: str, content: str
) -> LintContext:
    """Write a minimal technote.toml plus a content file, build a context.

    Also writes a sane ``requirements.txt`` so the structural requirements
    check (TN002/TN003) stays silent for content-focused tests that route
    through the full ``lint()`` aggregation.
    """
    (tmp_path / "technote.toml").write_text('[technote]\nid = "SQR-000"\n')
    (tmp_path / filename).write_text(content)
    (tmp_path / "requirements.txt").write_text("documenteer[technote]\n")
    return LintContext.from_dir(tmp_path, AuthorDb())


def _ipynb(*markdown_sources: str) -> str:
    """Serialize markdown cell sources into ``.ipynb`` JSON text."""
    cells = [
        {"cell_type": "markdown", "metadata": {}, "source": source}
        for source in markdown_sources
    ]
    return json.dumps(
        {"cells": cells, "metadata": {}, "nbformat": 4, "nbformat_minor": 5}
    )


RST_WITH_ABSTRACT = """\
#############
Demo technote
#############

.. abstract::

   A technote is a web-native single page document.

Introduction
============

Body text.
"""

MD_WITH_ABSTRACT = """\
# Demo technote

```{abstract}
A technote is a web-native single page document.
```

## Introduction

Body text.
"""

MD_WITH_COLON_ABSTRACT = """\
# Demo technote

:::{abstract}
A technote is a web-native single page document.
:::

## Introduction

Body text.
"""


def test_abstract_directive_rst_passes(tmp_path: Path) -> None:
    """A non-empty ``.. abstract::`` directive in index.rst passes."""
    context = _context_with_content(tmp_path, "index.rst", RST_WITH_ABSTRACT)
    assert check_abstract(context) == []


def test_abstract_directive_md_passes(tmp_path: Path) -> None:
    """A non-empty ```` ```{abstract} ```` fence in index.md passes."""
    context = _context_with_content(tmp_path, "index.md", MD_WITH_ABSTRACT)
    assert check_abstract(context) == []


def test_abstract_colon_directive_md_passes(tmp_path: Path) -> None:
    """A non-empty ``:::{abstract}`` fence in index.md passes."""
    context = _context_with_content(
        tmp_path, "index.md", MD_WITH_COLON_ABSTRACT
    )
    assert check_abstract(context) == []


def test_abstract_directive_ipynb_passes(tmp_path: Path) -> None:
    """A non-empty abstract directive in an index.ipynb cell passes."""
    content = _ipynb(
        "# Demo technote\n"
        "\n"
        "```{abstract}\n"
        "A technote is a web-native single page document.\n"
        "```",
        "## Introduction\n\nBody text.",
    )
    context = _context_with_content(tmp_path, "index.ipynb", content)
    assert check_abstract(context) == []


def test_rst_abstract_body_on_marker_line_passes(tmp_path: Path) -> None:
    """``.. abstract:: text`` is valid rST: the text is directive content."""
    content = (
        "#############\nDemo technote\n#############\n\n"
        ".. abstract:: A technote is a web-native single page document.\n\n"
        "Introduction\n============\n\nBody text.\n"
    )
    context = _context_with_content(tmp_path, "index.rst", content)
    assert check_abstract(context) == []


def test_mixed_case_rst_abstract_directive_passes(tmp_path: Path) -> None:
    """Docutils lowercases directive names, so ``.. Abstract::`` builds."""
    content = (
        "#############\nDemo technote\n#############\n\n"
        ".. Abstract::\n\n"
        "   A technote is a web-native single page document.\n\n"
        "Introduction\n============\n\nBody text.\n"
    )
    context = _context_with_content(tmp_path, "index.rst", content)
    assert check_abstract(context) == []


def test_mixed_case_myst_abstract_directive_passes(tmp_path: Path) -> None:
    """Docutils lowercases directive names, so ```{Abstract} builds."""
    content = (
        "# Demo technote\n\n"
        "```{Abstract}\n"
        "A technote is a web-native single page document.\n"
        "```\n\n"
        "## Introduction\n\nBody text.\n"
    )
    context = _context_with_content(tmp_path, "index.md", content)
    assert check_abstract(context) == []


def test_empty_myst_abstract_directive_reports_tn204(tmp_path: Path) -> None:
    """A MyST abstract fence with no body is reported with its location."""
    content = "# Demo technote\n\n```{abstract}\n```\n\n## Introduction\n"
    context = _context_with_content(tmp_path, "index.md", content)
    findings = check_abstract(context)
    assert [f.code for f in findings] == ["TN204"]
    assert findings[0].message.startswith("index.md:3:")
    # MyST content is pointed at the fenced directive, not the rST form.
    assert "```{abstract}" in findings[0].message
    assert ".. abstract::" not in findings[0].message


def test_unindented_rst_abstract_body_reports_tn204(tmp_path: Path) -> None:
    """An ``.. abstract::`` whose body is at column 0 is an empty directive."""
    content = """\
#############
Demo technote
#############

.. abstract::

A technote is a web-native single page document.

Introduction
============

Body text.
"""
    context = _context_with_content(tmp_path, "index.rst", content)
    findings = check_abstract(context)
    assert [f.code for f in findings] == ["TN204"]
    assert findings[0].severity is Severity.error
    assert findings[0].message.startswith("index.rst:5:")
    assert ".. abstract::" in findings[0].message


def test_no_abstract_reports_tn201(tmp_path: Path) -> None:
    """Content with neither a directive nor a heading yields TN201."""
    content = """\
#############
Demo technote
#############

Introduction
============

Body text.
"""
    context = _context_with_content(tmp_path, "index.rst", content)
    findings = check_abstract(context)
    assert [f.code for f in findings] == ["TN201"]
    assert findings[0].severity is Severity.error


def test_missing_content_file_yields_no_abstract_finding(
    tmp_path: Path,
) -> None:
    """A missing index file is TN006's business, not the abstract check's."""
    (tmp_path / "technote.toml").write_text('[technote]\nid = "SQR-000"\n')
    context = LintContext.from_dir(tmp_path, AuthorDb())
    assert check_abstract(context) == []


def test_conf_py_without_content_file_reports_tn006(tmp_path: Path) -> None:
    """A Sphinx technote with no index file yields TN006, not TN201."""
    (tmp_path / "technote.toml").write_text('[technote]\nid = "SQR-000"\n')
    (tmp_path / "conf.py").write_text(
        "from documenteer.conf.technote import *  # noqa: F401,F403\n"
    )
    (tmp_path / "requirements.txt").write_text("documenteer[technote]\n")
    context = LintContext.from_dir(tmp_path, AuthorDb())
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN006"]
    assert findings[0].severity is Severity.error


def test_abstract_heading_rst_reports_tn202(tmp_path: Path) -> None:
    """An ``Abstract`` section heading in index.rst yields TN202."""
    content = """\
#############
Demo technote
#############

Abstract
========

A technote is a web-native single page document.

Introduction
============

Body text.
"""
    context = _context_with_content(tmp_path, "index.rst", content)
    findings = check_abstract(context)
    assert [f.code for f in findings] == ["TN202"]
    assert findings[0].severity is Severity.error
    assert findings[0].message.startswith("index.rst:5:")
    assert ".. abstract::" in findings[0].message


def test_abstract_heading_md_reports_tn202(tmp_path: Path) -> None:
    """A Markdown ``## Abstract`` heading in index.md yields TN202."""
    content = """\
# Demo technote

## Abstract

A technote is a web-native single page document.

## Introduction

Body text.
"""
    context = _context_with_content(tmp_path, "index.md", content)
    findings = check_abstract(context)
    assert [f.code for f in findings] == ["TN202"]
    assert findings[0].message.startswith("index.md:3:")
    # MyST content is pointed at the fenced abstract directive, not the rST
    # form.
    assert "```{abstract}" in findings[0].message
    assert ".. abstract::" not in findings[0].message


def test_abstract_heading_ipynb_reports_tn202(tmp_path: Path) -> None:
    """A ``## Abstract`` heading in an index.ipynb cell yields TN202."""
    content = _ipynb(
        "# Demo technote",
        "## Abstract\n\nA technote is a web-native single page document.",
        "## Introduction\n\nBody text.",
    )
    context = _context_with_content(tmp_path, "index.ipynb", content)
    findings = check_abstract(context)
    assert [f.code for f in findings] == ["TN202"]
    # Notebook content is pointed at the fenced abstract directive.
    assert "```{abstract}" in findings[0].message
    assert ".. abstract::" not in findings[0].message


def test_abstract_via_rst_include_passes(tmp_path: Path) -> None:
    """An abstract factored into an rST ``.. include::`` file passes."""
    (tmp_path / "abstract.rst").write_text(
        ".. abstract::\n\n   A web-native single page document.\n"
    )
    content = (
        "#############\nDemo technote\n#############\n\n"
        ".. include:: abstract.rst\n\n"
        "Introduction\n============\n\nBody text.\n"
    )
    context = _context_with_content(tmp_path, "index.rst", content)
    assert check_abstract(context) == []


def test_abstract_via_myst_include_passes(tmp_path: Path) -> None:
    """An abstract factored into a MyST ``{include}`` file passes."""
    (tmp_path / "abstract.md").write_text(
        "```{abstract}\nA web-native single page document.\n```\n"
    )
    content = (
        "# Demo technote\n\n"
        "```{include} abstract.md\n"
        "```\n\n"
        "## Introduction\n\nBody text.\n"
    )
    context = _context_with_content(tmp_path, "index.md", content)
    assert check_abstract(context) == []


def test_include_of_missing_file_reports_tn201(tmp_path: Path) -> None:
    """An include pointing at a missing file is ignored, not a crash."""
    content = (
        "#############\nDemo technote\n#############\n\n"
        ".. include:: nowhere.rst\n\n"
        "Introduction\n============\n\nBody text.\n"
    )
    context = _context_with_content(tmp_path, "index.rst", content)
    assert [f.code for f in check_abstract(context)] == ["TN201"]


def test_include_outside_technote_root_is_ignored(tmp_path: Path) -> None:
    """An include that escapes the technote root is not scanned."""
    (tmp_path / "abstract.rst").write_text(
        ".. abstract::\n\n   A web-native single page document.\n"
    )
    root = tmp_path / "technote"
    root.mkdir()
    content = (
        "#############\nDemo technote\n#############\n\n"
        ".. include:: ../abstract.rst\n\n"
        "Introduction\n============\n\nBody text.\n"
    )
    context = _context_with_content(root, "index.rst", content)
    assert [f.code for f in check_abstract(context)] == ["TN201"]


def test_empty_notebook_abstract_reports_tn204_without_line(
    tmp_path: Path,
) -> None:
    """A notebook's cells are concatenated, so no line number is reported."""
    content = _ipynb(
        "# Demo technote\n\n```{abstract}\n```",
        "## Introduction\n\nBody text.",
    )
    context = _context_with_content(tmp_path, "index.ipynb", content)
    findings = check_abstract(context)
    assert [f.code for f in findings] == ["TN204"]
    assert findings[0].message.startswith("index.ipynb: ")


def test_corrupt_notebook_reports_tn203(tmp_path: Path) -> None:
    """A content notebook that is not valid JSON yields a TN203 error."""
    context = _context_with_content(tmp_path, "index.ipynb", "{ not json")
    findings = check_abstract(context)
    assert [f.code for f in findings] == ["TN203"]
    assert findings[0].severity is Severity.error


def test_myst_options_only_abstract_reports_tn204(tmp_path: Path) -> None:
    """A MyST abstract directive with only options is treated as empty."""
    content = (
        "# Demo technote\n\n"
        "```{abstract}\n"
        ":class: dropdown\n"
        "```\n\n"
        "## Introduction\n\nBody text.\n"
    )
    context = _context_with_content(tmp_path, "index.md", content)
    assert [f.code for f in check_abstract(context)] == ["TN204"]


def test_rst_options_only_abstract_reports_tn204(tmp_path: Path) -> None:
    """An rST abstract directive with only options is treated as empty."""
    content = (
        "#############\nDemo technote\n#############\n\n"
        ".. abstract::\n"
        "   :class: dropdown\n\n"
        "Introduction\n============\n\nBody text.\n"
    )
    context = _context_with_content(tmp_path, "index.rst", content)
    assert [f.code for f in check_abstract(context)] == ["TN204"]


def test_setext_abstract_heading_md_reports_tn202(tmp_path: Path) -> None:
    """A Setext ``Abstract``/``----`` heading in index.md yields TN202."""
    content = (
        "# Demo technote\n\n"
        "Abstract\n--------\n\n"
        "A technote is a web-native single page document.\n\n"
        "## Introduction\n\nBody text.\n"
    )
    context = _context_with_content(tmp_path, "index.md", content)
    findings = check_abstract(context)
    assert [f.code for f in findings] == ["TN202"]
    assert "```{abstract}" in findings[0].message


def test_setext_abstract_heading_ipynb_reports_tn202(tmp_path: Path) -> None:
    """A Setext ``Abstract``/``====`` heading in a notebook yields TN202."""
    content = _ipynb(
        "# Demo technote",
        "Abstract\n========\n\n"
        "A technote is a web-native single page document.",
        "## Introduction\n\nBody text.",
    )
    context = _context_with_content(tmp_path, "index.ipynb", content)
    findings = check_abstract(context)
    assert [f.code for f in findings] == ["TN202"]


def test_abstract_finding_surfaces_through_lint(tmp_path: Path) -> None:
    """check_abstract's findings are aggregated by the service."""
    context = _context_with_content(
        tmp_path,
        "index.rst",
        "#####\nTitle\n#####\n\nIntroduction\n============\n\nBody.\n",
    )
    service = TechnoteLintService(context)
    assert [f.code for f in service.lint()] == ["TN201"]


def _context_with_requirements(
    tmp_path: Path, requirements_text: str
) -> LintContext:
    """Write a minimal technote.toml plus a requirements.txt, build a context.

    ``check_requirements`` reads only ``requirements_text``, so no content
    file is needed for these structural tests.
    """
    (tmp_path / "technote.toml").write_text('[technote]\nid = "SQR-000"\n')
    (tmp_path / "requirements.txt").write_text(requirements_text)
    return LintContext.from_dir(tmp_path, AuthorDb())


def test_sane_requirements_pass(tmp_path: Path) -> None:
    """documenteer[technote] with no separate sphinx pin has no findings."""
    context = _context_with_requirements(tmp_path, "documenteer[technote]\n")
    assert check_requirements(context) == []


def test_sane_requirements_with_floor_pin_pass(tmp_path: Path) -> None:
    """A version specifier on documenteer[technote] still passes."""
    context = _context_with_requirements(
        tmp_path,
        "# Project requirements\ndocumenteer[technote]>=1.0.0\n",
    )
    assert check_requirements(context) == []


def test_missing_documenteer_reports_tn002(tmp_path: Path) -> None:
    """requirements.txt without documenteer yields a TN002 warning."""
    context = _context_with_requirements(tmp_path, "sphinx-prompt\n")
    findings = check_requirements(context)
    assert [f.code for f in findings] == ["TN002"]
    assert findings[0].severity is Severity.warning


def test_documenteer_without_technote_extra_reports_tn002(
    tmp_path: Path,
) -> None:
    """Documenteer declared without the [technote] extra yields TN002."""
    context = _context_with_requirements(tmp_path, "documenteer\n")
    findings = check_requirements(context)
    assert [f.code for f in findings] == ["TN002"]
    assert findings[0].severity is Severity.warning


def test_documenteer_with_other_extra_reports_tn002(tmp_path: Path) -> None:
    """Documenteer with only a non-technote extra still yields TN002."""
    context = _context_with_requirements(tmp_path, "documenteer[guide]\n")
    assert [f.code for f in check_requirements(context)] == ["TN002"]


def test_documenteer_extra_aggregated_across_lines(tmp_path: Path) -> None:
    """The technote extra is honored even when split across two lines."""
    context = _context_with_requirements(
        tmp_path, "documenteer\ndocumenteer[technote]\n"
    )
    assert check_requirements(context) == []


def test_missing_requirements_file_reports_tn002(tmp_path: Path) -> None:
    """A technote directory with no requirements.txt yields TN002."""
    (tmp_path / "technote.toml").write_text('[technote]\nid = "SQR-000"\n')
    context = LintContext.from_dir(tmp_path, AuthorDb())
    assert [f.code for f in check_requirements(context)] == ["TN002"]


def test_sphinx_pinned_separately_reports_tn003(tmp_path: Path) -> None:
    """A separate sphinx requirement yields a TN003 warning."""
    context = _context_with_requirements(
        tmp_path, "documenteer[technote]\nsphinx==8.1.0\n"
    )
    findings = check_requirements(context)
    assert [f.code for f in findings] == ["TN003"]
    assert findings[0].severity is Severity.warning


def test_sphinx_declared_without_version_reports_tn003(tmp_path: Path) -> None:
    """An unversioned separate sphinx requirement still yields TN003."""
    context = _context_with_requirements(
        tmp_path, "documenteer[technote]\nSphinx\n"
    )
    assert [f.code for f in check_requirements(context)] == ["TN003"]


def test_requirements_drift_reports_both_warnings(tmp_path: Path) -> None:
    """Missing documenteer[technote] and a separate sphinx pin both fire."""
    context = _context_with_requirements(tmp_path, "sphinx==8.1.0\n")
    findings = check_requirements(context)
    assert [f.code for f in findings] == ["TN002", "TN003"]
    assert all(f.severity is Severity.warning for f in findings)


def test_requirements_findings_surface_through_lint(
    tmp_path: Path,
) -> None:
    """check_requirements' warnings are aggregated by the service."""
    (tmp_path / "technote.toml").write_text('[technote]\nid = "SQR-000"\n')
    (tmp_path / "index.rst").write_text(RST_WITH_ABSTRACT)
    (tmp_path / "requirements.txt").write_text("sphinx==8.1.0\n")
    context = LintContext.from_dir(tmp_path, AuthorDb())
    service = TechnoteLintService(context)
    findings = service.lint()
    # Warnings only (no author or abstract errors), so --strict would
    # promote exactly these to make the run fatal.
    assert [f.code for f in findings] == ["TN002", "TN003"]
    assert all(f.severity is Severity.warning for f in findings)


def test_every_rule_has_a_docs_landing_page() -> None:
    """Each registered rule code has a page under docs/technotes/lint/.

    The lint report's "Learn more" footer links each fired code to
    ``rule_url(code)``, which maps onto ``docs/technotes/lint/<code>.rst``
    on documenteer.lsst.io — so a rule without a page would ship a dead
    link.
    """
    docs_dir = Path(__file__).parents[2] / "docs" / "technotes" / "lint"
    for code in CHECKS:
        page = docs_dir / f"{code.lower()}.rst"
        assert page.is_file(), f"{code} has no docs page at {page}"
        # The page's title names the code, so a copied page that still
        # describes a different rule is caught too.
        assert f"({code})" in page.read_text(), (
            f"{page} does not title the {code} rule"
        )
        assert rule_url(code).endswith(f"/technotes/lint/{code.lower()}.html")


def test_orcid_lookup_beats_unusable_name_search(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """An exact ORCID lookup suggests where the name search cannot.

    This is the lsst/rtn-077 case: the technote spells the author's given
    name differently from the author database, so a name search returns
    several equally-good Joneses and suggests nothing, but the declared
    ORCID resolves exactly.
    """
    _mock_orcid_lookup(
        responses,
        "0000-0001-5916-0031",
        [
            _author_record(
                "jonesrl",
                "R. Lynne",
                "Jones",
                orcid="https://orcid.org/0000-0001-5916-0031",
            )
        ],
    )
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "Lynne"
name.family = "Jones"
orcid = "https://orcid.org/0000-0001-5916-0031"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN101"]
    assert findings[0].message == (
        "Author Lynne Jones is missing an internal_id. Did you mean "
        "'jonesrl' (R. Lynne Jones, matched by ORCID)? Run 'documenteer "
        "technote sync-authors' to add it."
    )
    # No name search is registered: a hit on the exact lookup short-circuits
    # it, which is what makes this case suggestable at all.
    assert len(responses.calls) == 1


def test_orcid_miss_falls_back_to_name_search(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """An ORCID nobody holds falls through to the name search."""
    _mock_orcid_lookup(responses, "0000-0001-5916-0031", [])
    _mock_name_search(
        responses,
        [
            _search_result("jonesrl", "R. Lynne", "Jones", 90.0),
            _search_result("jonesd", "Derek", "Jones", 70.0),
        ],
    )
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "Lynne"
name.family = "Jones"
orcid = "https://orcid.org/0000-0001-5916-0031"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN101"]
    assert findings[0].message == (
        "Author Lynne Jones is missing an internal_id. Did you mean "
        "'jonesrl' (R. Lynne Jones, matched by name)? Run 'documenteer "
        "technote sync-authors' after adding it."
    )


def test_invalid_orcid_falls_back_to_name_search(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """An ORCID the database rejects still leaves the name search.

    The technote package's ORCID validator is looser than Ook's, so a
    schema-valid ``technote.toml`` can still declare an identifier the author
    database answers 422 for.
    """
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors",
        body='{"detail": "Input should be a valid ORCID"}',
        content_type="application/json",
        status=422,
        match=[
            matchers.query_param_matcher(
                {"orcid": "0000-0003-3001-676X-EXTRA"}
            )
        ],
    )
    _mock_name_search(
        responses, [_search_result("jonesrl", "R. Lynne", "Jones", 90.0)]
    )
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "Lynne"
name.family = "Jones"
orcid = "https://orcid.org/0000-0003-3001-676X-extra"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN101"]
    assert "matched by name" in findings[0].message


def test_both_lookups_failing_keeps_plain_tn102_message(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A TN102 finding is untouched when every suggestion lookup fails."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/lynnej",
        body="Not found",
        status=404,
    )
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors",
        body="Internal server error",
        status=500,
    )
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "Lynne"
name.family = "Jones"
internal_id = "lynnej"
orcid = "https://orcid.org/0000-0001-5916-0031"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN102"]
    assert findings[0].severity is Severity.error
    assert findings[0].message == (
        "Author Lynne Jones has internal_id 'lynnej', which is not in the "
        "author database."
    )


def test_check_defaults_its_docs_url_to_the_documenteer_page() -> None:
    """A check that names no page documents itself on documenteer.lsst.io."""
    check = Check(
        code="TN999",
        name="a-rule",
        description="A rule.",
        severity=Severity.warning,
    )
    assert (
        check.docs_url
        == "https://documenteer.lsst.io/technotes/lint/tn999.html"
    )


def test_check_can_document_itself_elsewhere() -> None:
    """A rule set documented outside Documenteer names its own page.

    Rule codes are stable identifiers a repository configures against, so a
    rule set that moves — into the ``technote`` package, say — keeps its
    codes and changes only where it is documented.
    """
    check = Check(
        code="TN999",
        name="a-rule",
        description="A rule.",
        severity=Severity.warning,
        docs_url="https://example.org/rules/tn999.html",
    )
    assert check.docs_url == "https://example.org/rules/tn999.html"


IGNORE_TN105 = """
[technote.lint]
ignore = ["TN105"]
"""
"""The ``[technote.lint]`` table that switches the DataCite rule off."""


def test_ignored_rule_reports_nothing_and_asks_datacite_nothing(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A rule named in [technote.lint] ignore does not run at all.

    No DataCite request is the substance of the feature, not a detail: a
    permanently-warning rule that still leaves the machine on every run
    would only be half switched off. The registered record is deliberately
    not mocked here, so a request would fail the run's ``responses`` fixture
    rather than pass silently.
    """
    _mock_author(responses)
    context = _write_technote(tmp_path, CITABLE_TOML + IGNORE_TN105)
    assert TechnoteLintService(context).lint() == []
    assert not [
        call
        for call in responses.calls
        if "api.datacite.org" in str(call.request.url)
    ]


def test_ignored_rules_are_named_with_their_source(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """The run reports which rules it skipped and where that was configured."""
    _mock_author(responses)
    context = _write_technote(tmp_path, CITABLE_TOML + IGNORE_TN105)
    service = TechnoteLintService(context)
    service.lint()
    assert service.ignored_rules == [
        IgnoredRule(code="TN105", source=IgnoreSource.toml)
    ]


def test_ignored_author_rules_never_reach_the_author_database(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """Ignoring TN101-TN103 keeps the author database out of the run."""
    context = _write_technote(
        tmp_path,
        CITABLE_TOML
        + """
[technote.lint]
ignore = ["TN101", "TN102", "TN103", "TN105"]
""",
    )
    assert TechnoteLintService(context).lint() == []
    assert len(responses.calls) == 0


def test_unknown_ignore_code_reports_tn007(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A code no rule carries is reported, and the valid entries still hold."""
    _mock_author(responses)
    context = _write_technote(
        tmp_path,
        CITABLE_TOML
        + """
[technote.lint]
ignore = ["TN150", "TN105"]
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN007"]
    assert "TN150" in findings[0].message
    assert service.ignored_rules == [
        IgnoredRule(code="TN105", source=IgnoreSource.toml)
    ]
    assert not [
        call
        for call in responses.calls
        if "api.datacite.org" in str(call.request.url)
    ]


def test_non_list_ignore_reports_tn007(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """An ignore setting that is not an array ignores nothing."""
    _mock_author(responses)
    responses.get(
        DATACITE_URL,
        body=_datacite_body(),
        content_type="application/vnd.api+json",
        status=200,
    )
    context = _write_technote(
        tmp_path,
        CITABLE_TOML
        + """
[technote.lint]
ignore = "TN105"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN007"]
    assert "array of rule codes" in findings[0].message
    assert "a string" in findings[0].message
    assert service.ignored_rules == []


def test_non_string_ignore_entry_reports_tn007(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """An entry that is not a rule code is reported, entry by entry."""
    _mock_author(responses)
    context = _write_technote(
        tmp_path,
        CITABLE_TOML
        + """
[technote.lint]
ignore = [105, "TN105"]
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN007"]
    assert "105" in findings[0].message
    assert service.ignored_rules == [
        IgnoredRule(code="TN105", source=IgnoreSource.toml)
    ]


def test_non_table_lint_settings_reports_tn007(tmp_path: Path) -> None:
    """A [technote.lint] that is not a table has no settings to read."""
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"
title = "The technote"
lint = "off"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN007"]
    assert "[technote.lint]" in findings[0].message
    assert service.ignored_rules == []


def test_ignore_codes_are_matched_case_insensitively(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """``tn105`` names the same rule as ``TN105``."""
    _mock_author(responses)
    context = _write_technote(
        tmp_path,
        CITABLE_TOML
        + """
[technote.lint]
ignore = ["tn105"]
""",
    )
    service = TechnoteLintService(context)
    assert service.lint() == []
    assert service.ignored_rules == [
        IgnoredRule(code="TN105", source=IgnoreSource.toml)
    ]


def test_ignore_survives_a_schema_invalid_technote_toml(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A file that fails schema validation still configures the linter.

    The lint configuration is read from the file's own text rather than
    through technote's parsed model, precisely so that a technote can ignore
    a rule while another part of the file is what a rule is reporting on.
    """
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name = "Jonathan Sick"

[technote.lint]
ignore = ["TN001"]
""",
    )
    service = TechnoteLintService(context)
    assert service.lint() == []
    assert service.ignored_rules == [
        IgnoredRule(code="TN001", source=IgnoreSource.toml)
    ]


def test_command_line_ignore_combines_with_the_file(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """``--ignore`` adds to the file's list rather than replacing it."""
    context = _write_technote(
        tmp_path,
        CITABLE_TOML
        + """
[technote.lint]
ignore = ["TN105"]
""",
    )
    service = TechnoteLintService(context, ignore=["TN101", "TN102", "TN103"])
    assert service.lint() == []
    assert service.ignored_rules == [
        IgnoredRule(code="TN101", source=IgnoreSource.cli),
        IgnoredRule(code="TN102", source=IgnoreSource.cli),
        IgnoredRule(code="TN103", source=IgnoreSource.cli),
        IgnoredRule(code="TN105", source=IgnoreSource.toml),
    ]
    assert len(responses.calls) == 0


def test_unknown_command_line_ignore_code_reports_tn007(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A ``--ignore`` typo is validated the same way the file's list is."""
    _mock_author(responses)
    responses.get(
        DATACITE_URL,
        body=_datacite_body(),
        content_type="application/vnd.api+json",
        status=200,
    )
    context = _write_technote(tmp_path, CITABLE_TOML)
    service = TechnoteLintService(context, ignore=["TN150"])
    findings = service.lint()
    assert [f.code for f in findings] == ["TN007"]
    assert "--ignore" in findings[0].message
    assert service.ignored_rules == []
