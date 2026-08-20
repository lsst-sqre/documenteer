"""Tests for the TechnoteAuthorService class."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import pytest_responses  # noqa: F401
from responses import RequestsMock, matchers

from documenteer.services.technoteauthor import (
    SyncAction,
    TechnoteAuthorService,
)
from documenteer.storage.authordb import AuthorDb, AuthorNotFoundError
from documenteer.storage.technotetoml import TechnoteTomlFile

SICK_ORCID = "https://orcid.org/0000-0003-3001-676X"
"""Jonathan Sick's ORCID, as a technote.toml spells it."""

JONES_ORCID = "https://orcid.org/0000-0001-5916-0031"
"""R. Lynne Jones's ORCID, as a technote.toml spells it."""


def _author_record(
    internal_id: str,
    given_name: str,
    family_name: str,
    orcid: str | None = None,
) -> dict[str, object]:
    """Build one entry of an Ook ORCID-lookup response body."""
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
    """Register Ook's exact ORCID lookup.

    ``orcid`` is the bare identifier the service is expected to put on the
    wire, so registering it with a query matcher also asserts that the URL
    form the caller passed was reduced by ``normalize_orcid``.
    """
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors",
        body=json.dumps(records),
        content_type="application/json",
        status=200,
        match=[matchers.query_param_matcher({"orcid": orcid})],
    )


def _mock_author_lookup(
    responses: RequestsMock,
    internal_id: str,
    record: dict[str, object] | None,
) -> None:
    """Register Ook's by-ID author lookup, or the 404 for no ``record``."""
    url = f"https://roundtable.lsst.cloud/ook/authors/{internal_id}"
    if record is None:
        responses.get(url, body="Not found", status=404)
    else:
        responses.get(
            url,
            body=json.dumps(record),
            content_type="application/json",
            status=200,
        )


def _service(toml_content: str) -> TechnoteAuthorService:
    """Build a service over an in-memory technote.toml."""
    return TechnoteAuthorService(TechnoteTomlFile(toml_content), AuthorDb())


def test_add_author_by_orcid(responses: RequestsMock) -> None:
    """A known ORCID appends that author to technote.toml."""
    _mock_orcid_lookup(
        responses,
        "0000-0003-3001-676X",
        [_author_record("sickj", "Jonathan", "Sick", orcid=SICK_ORCID)],
    )
    service = _service(
        """
[technote]
id = "SQR-000"
"""
    )

    author = service.add_author_by_orcid(SICK_ORCID)

    assert author.internal_id == "sickj"
    assert service.toml_file.author_ids == ["sickj"]
    assert service.toml_file.authors_aot[0]["name"]["family"] == "Sick"


def test_add_author_by_orcid_updates_in_place(
    responses: RequestsMock,
) -> None:
    """An ORCID already listed updates that author rather than duplicating."""
    _mock_orcid_lookup(
        responses,
        "0000-0003-3001-676X",
        [_author_record("sickj", "Jonathan", "Sick", orcid=SICK_ORCID)],
    )
    service = _service(
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name = {given = "Jon", family = "Sick"}
internal_id = "sickj"
"""
    )

    service.add_author_by_orcid(SICK_ORCID)

    assert service.toml_file.author_ids == ["sickj"]
    assert service.toml_file.authors_aot[0]["name"]["given"] == "Jonathan"


def test_add_author_by_orcid_not_found(responses: RequestsMock) -> None:
    """A well-formed ORCID nobody holds raises AuthorNotFoundError."""
    _mock_orcid_lookup(responses, "0000-0001-5916-0031", [])
    service = _service(
        """
[technote]
id = "SQR-000"
"""
    )

    with pytest.raises(AuthorNotFoundError, match="0000-0001-5916-0031"):
        service.add_author_by_orcid("https://orcid.org/0000-0001-5916-0031")

    assert service.toml_file.author_ids == []


def test_sync_authors_repairs_wrong_id_by_orcid(
    responses: RequestsMock,
) -> None:
    """A 404 internal_id is rewritten in place from the declared ORCID."""
    _mock_author_lookup(responses, "lynnej", None)
    _mock_orcid_lookup(
        responses,
        "0000-0001-5916-0031",
        [_author_record("jonesrl", "R. Lynne", "Jones", orcid=JONES_ORCID)],
    )
    service = _service(
        f"""
[technote]
id = "SQR-000"

[[technote.authors]]
name = {{given = "Lynne", family = "Jones"}}
internal_id = "lynnej"
orcid = "{JONES_ORCID}"
"""
    )

    outcomes = service.sync_authors()

    assert [o.action for o in outcomes] == [SyncAction.repaired]
    assert outcomes[0].previous_internal_id == "lynnej"
    assert outcomes[0].author is not None
    assert outcomes[0].author.internal_id == "jonesrl"
    # The repair edits the one entry rather than appending a corrected copy.
    assert len(service.toml_file.authors_aot) == 1
    assert service.toml_file.author_ids == ["jonesrl"]


def test_sync_authors_fills_missing_id_from_orcid(
    responses: RequestsMock,
) -> None:
    """An entry with no internal_id gets one from its declared ORCID."""
    _mock_orcid_lookup(
        responses,
        "0000-0001-5916-0031",
        [_author_record("jonesrl", "R. Lynne", "Jones", orcid=JONES_ORCID)],
    )
    service = _service(
        f"""
[technote]
id = "SQR-000"

[[technote.authors]]
name = {{given = "Lynne", family = "Jones"}}
orcid = "{JONES_ORCID}"
"""
    )

    outcomes = service.sync_authors()

    assert [o.action for o in outcomes] == [SyncAction.filled]
    assert outcomes[0].previous_internal_id is None
    assert service.toml_file.author_ids == ["jonesrl"]


def test_sync_authors_skips_unresolvable_and_continues(
    responses: RequestsMock,
) -> None:
    """One unrepairable author no longer costs the others their update."""
    _mock_author_lookup(responses, "nobody", None)
    _mock_author_lookup(
        responses,
        "sickj",
        _author_record("sickj", "Jonathan", "Sick", orcid=SICK_ORCID),
    )
    service = _service(
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name = {given = "No", family = "Body"}
internal_id = "nobody"

[[technote.authors]]
name = {given = "Jon", family = "Sick"}
internal_id = "sickj"
"""
    )

    outcomes = service.sync_authors()

    assert [o.action for o in outcomes] == [
        SyncAction.skipped,
        SyncAction.synced,
    ]
    assert outcomes[0].reason == (
        "Could not sync author No Body: internal_id 'nobody' is not in the "
        "Rubin author database, and the entry declares no ORCID to fall "
        "back on."
    )
    # The unresolvable entry is left exactly as declared...
    assert service.toml_file.author_ids == ["nobody", "sickj"]
    # ...while the resolvable one is still synchronized.
    assert service.toml_file.authors_aot[1]["name"]["given"] == "Jonathan"


def test_sync_authors_leaves_a_healthy_file_byte_identical(
    responses: RequestsMock, tmp_path: Path
) -> None:
    """A technote whose IDs all resolve is rewritten byte for byte."""
    _mock_author_lookup(
        responses,
        "sickj",
        _author_record("sickj", "Jonathan", "Sick", orcid=SICK_ORCID),
    )
    content = f"""
[technote]
id = "SQR-000"

[[technote.authors]]
name = {{given = "Jonathan", family = "Sick"}}
internal_id = "sickj"
orcid = "{SICK_ORCID}"
"""
    service = _service(content)

    outcomes = service.sync_authors()

    assert [o.action for o in outcomes] == [SyncAction.synced]
    path = tmp_path / "technote.toml"
    service.write_toml(path)
    assert path.read_text() == content


def test_sync_authors_skips_a_malformed_id_record(
    responses: RequestsMock,
) -> None:
    """A 200 that is not an author record skips that entry, not the run."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/sickj",
        body='{"not": "an author"}',
        content_type="application/json",
        status=200,
    )
    _mock_author_lookup(
        responses,
        "jonesrl",
        _author_record("jonesrl", "R. Lynne", "Jones", orcid=JONES_ORCID),
    )
    service = _service(
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name = {given = "Jon", family = "Sick"}
internal_id = "sickj"

[[technote.authors]]
name = {given = "Lynne", family = "Jones"}
internal_id = "jonesrl"
"""
    )

    outcomes = service.sync_authors()

    assert [o.action for o in outcomes] == [
        SyncAction.skipped,
        SyncAction.synced,
    ]
    assert outcomes[0].reason == (
        "Could not sync author Jon Sick: the Rubin author database returned "
        "a malformed record for internal_id 'sickj'."
    )
    # The other author is still synchronized: one bad record is not the run.
    assert service.toml_file.authors_aot[1]["name"]["given"] == "R. Lynne"


def test_sync_authors_skips_a_malformed_orcid_record(
    responses: RequestsMock,
) -> None:
    """A malformed ORCID-lookup body skips that entry, not the run."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors",
        body='{"not": "a listing"}',
        content_type="application/json",
        status=200,
        match=[matchers.query_param_matcher({"orcid": "0000-0001-5916-0031"})],
    )
    service = _service(
        f"""
[technote]
id = "SQR-000"

[[technote.authors]]
name = {{given = "Lynne", family = "Jones"}}
orcid = "{JONES_ORCID}"
"""
    )

    outcomes = service.sync_authors()

    assert [o.action for o in outcomes] == [SyncAction.skipped]
    assert outcomes[0].reason == (
        "Could not sync author Lynne Jones: the Rubin author database "
        f"returned a malformed record for ORCID {JONES_ORCID}."
    )
    assert service.toml_file.author_ids == []


def test_sync_authors_skips_a_repair_that_duplicates_an_entry(
    responses: RequestsMock,
) -> None:
    """A repair onto an ID another entry declares is reported, not written."""
    _mock_author_lookup(
        responses,
        "jonesrl",
        _author_record("jonesrl", "R. Lynne", "Jones", orcid=JONES_ORCID),
    )
    _mock_author_lookup(responses, "lynnej", None)
    _mock_orcid_lookup(
        responses,
        "0000-0001-5916-0031",
        [_author_record("jonesrl", "R. Lynne", "Jones", orcid=JONES_ORCID)],
    )
    service = _service(
        f"""
[technote]
id = "SQR-000"

[[technote.authors]]
name = {{given = "R. Lynne", family = "Jones"}}
internal_id = "jonesrl"

[[technote.authors]]
name = {{given = "Lynne", family = "Jones"}}
internal_id = "lynnej"
orcid = "{JONES_ORCID}"
"""
    )

    outcomes = service.sync_authors()

    assert [o.action for o in outcomes] == [
        SyncAction.synced,
        SyncAction.skipped,
    ]
    assert outcomes[1].reason == (
        "Could not sync author Lynne Jones: their ORCID resolves to "
        "internal_id 'jonesrl', which another author entry already declares. "
        "Remove whichever of the two entries is the duplicate."
    )
    # The technote is left with the duplicate it declared, not two jonesrl.
    assert service.toml_file.author_ids == ["jonesrl", "lynnej"]
