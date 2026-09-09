"""Tests for the datacite storage module."""

from __future__ import annotations

import json
from typing import Any

import pytest
import pytest_responses  # noqa: F401
import requests
from responses import RequestsMock

from documenteer.citations import PartialDate
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
    publication_year: int | None = 2026,
    dates: list[dict[str, Any]] | None = None,
) -> str:
    """Build a DataCite ``/dois/{id}`` response body.

    Only the fields the client reads are varied; the rest are present so the
    body is shaped like a real one, which is what makes the extra-field
    tolerance meaningful. ``publication_year`` defaults to the 2026 a
    Rubin-minted record carries; passing `None` leaves the field out.
    """
    year = (
        {}
        if publication_year is None
        else {"publicationYear": publication_year}
    )
    return json.dumps(
        {
            "data": {
                "id": DOI,
                "type": "dois",
                "attributes": {
                    "doi": DOI,
                    "dates": dates if dates is not None else [],
                    # The record's own timestamps. They date the *DOI*, not
                    # the work, so a test that reads a date must never come
                    # out of them.
                    "created": "2019-01-01T00:00:00.000Z",
                    "registered": "2019-01-01T00:00:00.000Z",
                    "updated": "2019-01-01T00:00:00.000Z",
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
                    **year,
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


def test_get_record_reads_the_publication_year(
    responses: RequestsMock,
) -> None:
    """A Rubin-minted record is dated by its mandatory ``publicationYear``.

    This is the live shape of ``10.71929/rubin/3382539``: a
    ``publicationYear`` and an empty ``dates`` list. DataCite defines
    ``publicationYear`` as the year the resource was made publicly
    available — the citation year — so a record that states nothing finer
    is still dated, to the year.
    """
    responses.get(
        RECORD_URL,
        body=_payload(),
        content_type="application/vnd.api+json",
        status=200,
    )
    record = DataCiteClient().get_record(DOI)
    assert record is not None
    assert record.publication_year == 2026
    assert record.issued == PartialDate(2026)


def test_get_record_prefers_an_issued_date(responses: RequestsMock) -> None:
    """An ``Issued``-typed date states the same publication to the day.

    This is the live shape of the Zenodo legacy record
    ``10.5281/zenodo.51968``: ``publicationYear`` 2016 alongside an
    ``Issued`` date of 2016-05-24.
    """
    responses.get(
        RECORD_URL,
        body=_payload(
            publication_year=2016,
            dates=[{"date": "2016-05-24", "dateType": "Issued"}],
        ),
        content_type="application/vnd.api+json",
        status=200,
    )
    record = DataCiteClient().get_record(DOI)
    assert record is not None
    assert record.publication_year == 2016
    assert record.issued == PartialDate(2016, 5, 24)


def test_get_record_reads_an_issued_date_at_its_own_precision(
    responses: RequestsMock,
) -> None:
    """A reduced-precision ``Issued`` date is not padded out to a day."""
    responses.get(
        RECORD_URL,
        body=_payload(
            publication_year=2016,
            dates=[{"date": "2016-05", "dateType": "issued"}],
        ),
        content_type="application/vnd.api+json",
        status=200,
    )
    record = DataCiteClient().get_record(DOI)
    assert record is not None
    assert record.issued == PartialDate(2016, 5)


def test_get_record_ignores_a_date_that_is_not_an_issue_date(
    responses: RequestsMock,
) -> None:
    """Only an ``Issued`` entry dates the work.

    ``Submitted``, ``Available``, ``Updated`` and the rest describe other
    moments in a resource's life, so the record falls back to the year
    DataCite calls the publication year.
    """
    responses.get(
        RECORD_URL,
        body=_payload(
            publication_year=2016,
            dates=[
                {"date": "2015-11-02", "dateType": "Submitted"},
                {"date": "2020-07-19", "dateType": "Updated"},
            ],
        ),
        content_type="application/vnd.api+json",
        status=200,
    )
    record = DataCiteClient().get_record(DOI)
    assert record is not None
    assert record.issued == PartialDate(2016)


def test_get_record_ignores_an_unreadable_issued_date(
    responses: RequestsMock,
) -> None:
    """A date DataCite allows but ISO 8601 precision cannot express.

    DataCite's ``dates`` accepts a range (``2004-03-02/2005-06-02``), which
    is not a publication date at any of the three precisions, so the record
    falls back to the publication year rather than failing the read.
    """
    responses.get(
        RECORD_URL,
        body=_payload(
            publication_year=2016,
            dates=[{"date": "2004-03-02/2005-06-02", "dateType": "Issued"}],
        ),
        content_type="application/vnd.api+json",
        status=200,
    )
    record = DataCiteClient().get_record(DOI)
    assert record is not None
    assert record.issued == PartialDate(2016)


def test_get_record_reads_an_undated_record(responses: RequestsMock) -> None:
    """A record with neither field states no date at all.

    ``publicationYear`` is mandatory in DataCite's schema, so this shape
    should not occur — but a read that invents a date for it would be worse
    than one that reports the record as undated.
    """
    responses.get(
        RECORD_URL,
        body=_payload(publication_year=None),
        content_type="application/vnd.api+json",
        status=200,
    )
    record = DataCiteClient().get_record(DOI)
    assert record is not None
    assert record.publication_year is None
    assert record.issued is None


def test_get_record_ignores_a_publication_year_that_is_not_a_year(
    responses: RequestsMock,
) -> None:
    """A year outside ISO 8601's four digits dates nothing."""
    responses.get(
        RECORD_URL,
        body=_payload(publication_year=0),
        content_type="application/vnd.api+json",
        status=200,
    )
    record = DataCiteClient().get_record(DOI)
    assert record is not None
    assert record.publication_year == 0
    assert record.issued is None


def test_get_record_never_dates_a_work_by_its_doi_record(
    responses: RequestsMock,
) -> None:
    """The record-level timestamps are not read.

    ``created``/``registered``/``updated`` date the DOI record itself — when
    the DOI was minted and last touched — not when the technote was
    published. `_payload` stamps them 2019 so a read that consulted them
    would show up here.
    """
    responses.get(
        RECORD_URL,
        body=_payload(
            publication_year=2016,
            dates=[{"date": "2016-05-24", "dateType": "Issued"}],
        ),
        content_type="application/vnd.api+json",
        status=200,
    )
    record = DataCiteClient().get_record(DOI)
    assert record is not None
    assert record.issued == PartialDate(2016, 5, 24)
    assert record.publication_year == 2016
