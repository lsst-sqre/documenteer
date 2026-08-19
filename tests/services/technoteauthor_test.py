"""Tests for the TechnoteAuthorService class."""

from __future__ import annotations

import json

import pytest
import pytest_responses  # noqa: F401
from responses import RequestsMock, matchers

from documenteer.services.technoteauthor import TechnoteAuthorService
from documenteer.storage.authordb import AuthorDb, AuthorNotFoundError
from documenteer.storage.technotetoml import TechnoteTomlFile

SICK_ORCID = "https://orcid.org/0000-0003-3001-676X"
"""Jonathan Sick's ORCID, as a technote.toml spells it."""


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
