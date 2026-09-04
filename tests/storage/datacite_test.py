"""Tests for the datacite storage module."""

from __future__ import annotations

import json
from typing import Any

import pytest
import pytest_responses  # noqa: F401
import requests
from responses import RequestsMock

from documenteer.storage.datacite import (
    DataCiteClient,
    DataCiteCreator,
    DataCiteUnavailableError,
    datacite_api_url,
)

DOI = "10.71929/rubin/2570308"
"""The DOI every test in this module asks about."""

RECORD_URL = f"https://api.datacite.org/dois/{DOI}"
"""The API URL that DOI's registered metadata is read from."""


def _payload(
    *,
    titles: list[dict[str, Any]] | None = None,
    creators: list[dict[str, Any]] | None = None,
) -> str:
    """Build a DataCite ``/dois/{id}`` response body.

    Only the fields the client reads are varied; the rest are present so the
    body is shaped like a real one, which is what makes the extra-field
    tolerance meaningful.
    """
    return json.dumps(
        {
            "data": {
                "id": DOI,
                "type": "dois",
                "attributes": {
                    "doi": DOI,
                    "titles": (
                        titles
                        if titles is not None
                        else [{"title": "The technote"}]
                    ),
                    "creators": (
                        creators
                        if creators is not None
                        else [
                            {
                                "name": "Sick, Jonathan",
                                "nameType": "Personal",
                                "givenName": "Jonathan",
                                "familyName": "Sick",
                                "affiliation": [],
                                "nameIdentifiers": [
                                    {
                                        "nameIdentifier": (
                                            "https://orcid.org/"
                                            "0000-0003-3001-676X"
                                        ),
                                        "nameIdentifierScheme": "ORCID",
                                        "schemeUri": "https://orcid.org",
                                    }
                                ],
                            }
                        ]
                    ),
                    "publisher": "Vera C. Rubin Observatory",
                    "publicationYear": 2026,
                    "url": "https://sqr-000.lsst.io/",
                    "state": "findable",
                },
            }
        }
    )


def test_datacite_api_url_normalizes_the_doi() -> None:
    """Every spelling of a DOI addresses the same API record."""
    assert datacite_api_url(DOI) == RECORD_URL
    assert datacite_api_url(f"https://doi.org/{DOI}") == RECORD_URL
    assert datacite_api_url(f"doi:{DOI}") == RECORD_URL


def test_datacite_api_url_rejects_a_non_doi() -> None:
    """A value that is not a DOI has no record URL."""
    with pytest.raises(ValueError, match="Not a DOI"):
        datacite_api_url("10.71929")


def test_get_record_reads_title_and_creators(responses: RequestsMock) -> None:
    """A registered DOI yields its title, creators, and record URL."""
    responses.get(
        RECORD_URL,
        body=_payload(),
        content_type="application/vnd.api+json",
        status=200,
    )
    record = DataCiteClient().get_record(DOI)
    assert record is not None
    assert record.doi == DOI
    assert record.title == "The technote"
    assert record.creators == (
        DataCiteCreator(
            name_type="Personal",
            given_name="Jonathan",
            family_name="Sick",
            name="Sick, Jonathan",
            orcid="0000-0003-3001-676X",
        ),
    )
    assert record.url == RECORD_URL


def test_get_record_accepts_a_doi_url(responses: RequestsMock) -> None:
    """A DOI given as a doi.org URL is normalized before it goes on the
    wire.
    """
    responses.get(
        RECORD_URL,
        body=_payload(),
        content_type="application/vnd.api+json",
        status=200,
    )
    record = DataCiteClient().get_record(f"https://doi.org/{DOI}")
    assert record is not None
    assert record.doi == DOI


def test_get_record_prefers_the_main_title(responses: RequestsMock) -> None:
    """An alternative title is not mistaken for the title of the work."""
    responses.get(
        RECORD_URL,
        body=_payload(
            titles=[
                {"title": "A subtitle", "titleType": "Subtitle"},
                {"title": "The technote"},
            ]
        ),
        content_type="application/vnd.api+json",
        status=200,
    )
    record = DataCiteClient().get_record(DOI)
    assert record is not None
    assert record.title == "The technote"


def test_get_record_reads_an_organizational_creator(
    responses: RequestsMock,
) -> None:
    """An organizational creator carries its whole name and no name parts."""
    responses.get(
        RECORD_URL,
        body=_payload(
            creators=[
                {
                    "name": "Vera C. Rubin Observatory",
                    "nameType": "Organizational",
                    "nameIdentifiers": [],
                    "affiliation": [],
                }
            ]
        ),
        content_type="application/vnd.api+json",
        status=200,
    )
    record = DataCiteClient().get_record(DOI)
    assert record is not None
    assert record.creators == (
        DataCiteCreator(
            name_type="Organizational",
            given_name=None,
            family_name=None,
            name="Vera C. Rubin Observatory",
            orcid=None,
        ),
    )


def test_get_record_reads_a_family_name_only_creator(
    responses: RequestsMock,
) -> None:
    """A ``Personal`` creator with only a family name keeps its ``null``.

    This is the shape Rubin's minter registers a committee in: ``nameType``
    is ``Personal`` and only ``familyName`` is deposited, which leaves the
    formatted ``name`` carrying a literal ``null`` for the absent given name.
    The record hands both spellings on unedited; deciding which to believe
    belongs to the comparison, not to the read.
    """
    responses.get(
        RECORD_URL,
        body=_payload(
            creators=[
                {
                    "name": "Rubin's Survey Cadence Optimization "
                    "Committee, null",
                    "nameType": "Personal",
                    "familyName": "Rubin's Survey Cadence Optimization "
                    "Committee",
                    "nameIdentifiers": [],
                    "affiliation": [],
                }
            ]
        ),
        content_type="application/vnd.api+json",
        status=200,
    )
    record = DataCiteClient().get_record(DOI)
    assert record is not None
    assert record.creators == (
        DataCiteCreator(
            name_type="Personal",
            given_name=None,
            family_name="Rubin's Survey Cadence Optimization Committee",
            name="Rubin's Survey Cadence Optimization Committee, null",
            orcid=None,
        ),
    )


def test_get_record_normalizes_a_creator_orcid(
    responses: RequestsMock,
) -> None:
    """An ORCID is reduced to the bare identifier, whatever its spelling.

    A creator's identifiers may include schemes other than ORCID, and only
    the ORCID one is read.
    """
    responses.get(
        RECORD_URL,
        body=_payload(
            creators=[
                {
                    "name": "Sick, Jonathan",
                    "nameType": "Personal",
                    "givenName": "Jonathan",
                    "familyName": "Sick",
                    "nameIdentifiers": [
                        {
                            "nameIdentifier": "https://ror.org/048g3cy84",
                            "nameIdentifierScheme": "ROR",
                        },
                        {
                            "nameIdentifier": "0000-0003-3001-676x",
                            "nameIdentifierScheme": "orcid",
                        },
                    ],
                }
            ]
        ),
        content_type="application/vnd.api+json",
        status=200,
    )
    record = DataCiteClient().get_record(DOI)
    assert record is not None
    assert record.creators[0].orcid == "0000-0003-3001-676X"


def test_get_record_returns_none_when_unregistered(
    responses: RequestsMock,
) -> None:
    """A DOI DataCite does not know is not an error."""
    responses.get(
        RECORD_URL,
        body='{"errors":[{"status":"404","title":"The resource you are '
        "looking for doesn't exist.\"}]}",
        content_type="application/vnd.api+json",
        status=404,
    )
    assert DataCiteClient().get_record(DOI) is None


def test_get_record_raises_when_unreachable(responses: RequestsMock) -> None:
    """A connection failure is reported as an unavailable DataCite."""
    responses.get(RECORD_URL, body=requests.ConnectionError("no route"))
    with pytest.raises(DataCiteUnavailableError):
        DataCiteClient().get_record(DOI)


def test_get_record_raises_on_timeout(responses: RequestsMock) -> None:
    """A request that times out is reported as an unavailable DataCite."""
    responses.get(RECORD_URL, body=requests.ReadTimeout("too slow"))
    with pytest.raises(DataCiteUnavailableError):
        DataCiteClient().get_record(DOI)


def test_get_record_raises_on_server_error(responses: RequestsMock) -> None:
    """A 5xx is reported as an unavailable DataCite, not as an unregistered
    DOI.
    """
    responses.get(RECORD_URL, body="oops", status=503)
    with pytest.raises(DataCiteUnavailableError):
        DataCiteClient().get_record(DOI)


def test_get_record_raises_on_unusable_payload(
    responses: RequestsMock,
) -> None:
    """A body that is not a DOI record is reported as an unavailable
    DataCite.
    """
    responses.get(
        RECORD_URL,
        body='{"meta": {}}',
        content_type="application/vnd.api+json",
        status=200,
    )
    with pytest.raises(DataCiteUnavailableError):
        DataCiteClient().get_record(DOI)


def test_get_record_rejects_a_non_doi() -> None:
    """A value that is not a DOI is refused before any request is made."""
    with pytest.raises(ValueError, match="Not a DOI"):
        DataCiteClient().get_record("10.71929")
