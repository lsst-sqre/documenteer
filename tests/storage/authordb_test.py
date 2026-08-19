"""tests for the authordb storage module."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest
import pytest_responses  # noqa: F401
import requests
from responses import RequestsMock

from documenteer.storage.authordb import (
    AuthorDb,
    AuthorDbUnreachableError,
    AuthorNotFoundError,
    InvalidOrcidError,
)

SEARCH_JSON = """
[
    {
        "affiliations": [],
        "family_name": "Jones",
        "given_name": "R. Lynne",
        "internal_id": "jonesrl",
        "notes": [],
        "orcid": "https://orcid.org/0000-0001-5916-0031",
        "score": 90.0
    },
    {
        "affiliations": [],
        "family_name": "Jones",
        "given_name": "Derek",
        "internal_id": "jonesd",
        "notes": [],
        "orcid": null,
        "score": 70.0
    }
]
"""


ORCID_JSON = """
[
    {
        "affiliations": [],
        "family_name": "Jones",
        "given_name": "R. Lynne",
        "internal_id": "jonesrl",
        "notes": [],
        "orcid": "https://orcid.org/0000-0001-5916-0031"
    }
]
"""


def test_from_yaml(responses: RequestsMock) -> None:
    response_data = """
{
    "affiliations": [
        {
            "address": {
                "city": "Ontario",
                "country": "Canada",
                "postal_code": null,
                "state": null,
                "street": "Penetanguishene"
            },
            "department": null,
            "internal_id": "JSickCodes",
            "name": "J.Sick Codes Inc.",
            "ror": null
        },
        {
            "address": {
                "city": "Tucson",
                "country": "USA",
                "postal_code": "85719",
                "state": "AZ",
                "street": "950 N. Cherry Ave."
            },
            "department": null,
            "internal_id": "RubinObs",
            "name": "Vera C. Rubin Observatory Project Office",
            "ror": "https://ror.org/048g3cy84"
        }
    ],
    "family_name": "Sick",
    "given_name": "Jonathan",
    "internal_id": "sickj",
    "notes": [],
    "orcid": "https://orcid.org/0000-0003-3001-676X"
}
"""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/sickj",
        body=response_data,
        content_type="application/json",
        status=200,
    )

    author_db = AuthorDb()
    author = author_db.get_author("sickj")
    assert author.family_name == "Sick"
    assert author.given_name == "Jonathan"
    assert author.internal_id == "sickj"
    assert str(author.orcid) == "https://orcid.org/0000-0003-3001-676X"
    assert author.affiliations[0].internal_id == "JSickCodes"
    assert author.affiliations[0].name == "J.Sick Codes Inc."
    assert str(author.affiliations[1].ror) == "https://ror.org/048g3cy84"


def test_get_author_not_found(responses: RequestsMock) -> None:
    """A 404 response raises ``AuthorNotFoundError``."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/nobody",
        body="Not found",
        status=404,
    )

    author_db = AuthorDb()
    with pytest.raises(AuthorNotFoundError):
        author_db.get_author("nobody")


def test_get_author_transport_error(responses: RequestsMock) -> None:
    """A transport failure raises ``AuthorDbUnreachableError``."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/sickj",
        body=requests.ConnectionError("connection refused"),
    )

    author_db = AuthorDb()
    with pytest.raises(ValueError, match="Failed to fetch author") as exc_info:
        author_db.get_author("sickj")
    assert isinstance(exc_info.value, AuthorDbUnreachableError)
    assert not isinstance(exc_info.value, AuthorNotFoundError)


def test_search_authors(responses: RequestsMock) -> None:
    """A name search returns scored author results, best match first."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors",
        body=SEARCH_JSON,
        content_type="application/json",
        status=200,
    )

    author_db = AuthorDb()
    results = author_db.search_authors("Jones, Lynne")
    assert [r.internal_id for r in results] == ["jonesrl", "jonesd"]
    assert results[0].score == 90.0
    assert str(results[0].orcid) == "https://orcid.org/0000-0001-5916-0031"
    assert results[1].orcid is None
    query = parse_qs(urlparse(responses.calls[0].request.url or "").query)
    assert query["search"] == ["Jones, Lynne"]
    assert query["limit"] == ["10"]


def test_search_authors_transport_error(responses: RequestsMock) -> None:
    """A failed search raises ``AuthorDbUnreachableError``."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors",
        body="Internal server error",
        status=500,
    )

    author_db = AuthorDb()
    with pytest.raises(AuthorDbUnreachableError):
        author_db.search_authors("Jones, Lynne")


def test_get_author_server_error(responses: RequestsMock) -> None:
    """A non-404 HTTP error is a transport error, not a not-found."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/sickj",
        body="Internal server error",
        status=500,
    )

    author_db = AuthorDb()
    with pytest.raises(ValueError, match="Failed to fetch author") as exc_info:
        author_db.get_author("sickj")
    assert isinstance(exc_info.value, AuthorDbUnreachableError)
    assert not isinstance(exc_info.value, AuthorNotFoundError)


def test_get_author_by_orcid(responses: RequestsMock) -> None:
    """An ORCID lookup that hits returns the one matching author."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors",
        body=ORCID_JSON,
        content_type="application/json",
        status=200,
    )

    author_db = AuthorDb()
    author = author_db.get_author_by_orcid(
        "https://orcid.org/0000-0001-5916-0031"
    )
    assert author is not None
    assert author.internal_id == "jonesrl"
    assert author.given_name == "R. Lynne"
    query = parse_qs(urlparse(responses.calls[0].request.url or "").query)
    assert query == {"orcid": ["0000-0001-5916-0031"]}


def test_get_author_by_orcid_miss(responses: RequestsMock) -> None:
    """A well-formed ORCID nobody holds is an ordinary miss, not an error."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors",
        body="[]",
        content_type="application/json",
        status=200,
    )

    author_db = AuthorDb()
    assert author_db.get_author_by_orcid("0000-0001-5916-0032") is None


def test_get_author_by_orcid_invalid(responses: RequestsMock) -> None:
    """A 422 response means bad input, not an unreachable database."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors",
        body='{"detail": "Input should be a valid ORCID"}',
        content_type="application/json",
        status=422,
    )

    author_db = AuthorDb()
    with pytest.raises(InvalidOrcidError):
        author_db.get_author_by_orcid("not-an-orcid")


def test_get_author_by_orcid_server_error(responses: RequestsMock) -> None:
    """A 5xx response raises ``AuthorDbUnreachableError``."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors",
        body="Internal server error",
        status=500,
    )

    author_db = AuthorDb()
    with pytest.raises(AuthorDbUnreachableError) as exc_info:
        author_db.get_author_by_orcid("0000-0001-5916-0031")
    assert not isinstance(exc_info.value, InvalidOrcidError)


def test_get_author_by_orcid_transport_error(responses: RequestsMock) -> None:
    """A connection error raises ``AuthorDbUnreachableError``."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors",
        body=requests.ConnectionError("connection refused"),
    )

    author_db = AuthorDb()
    with pytest.raises(AuthorDbUnreachableError):
        author_db.get_author_by_orcid("0000-0001-5916-0031")


@pytest.mark.parametrize(
    "declared",
    [
        # str(Person.orcid) for each form technote.toml can declare. The
        # technote package's validator re-prefixes anything that does not
        # literally start with "https://orcid", so the last two are what a
        # http:// URL and a foreign-host URL become.
        "https://orcid.org/0000-0003-3001-676X",
        "https://orcid.org/0000-0003-3001-676X/",
        "https://orcid.org/http://orcid.org/0000-0003-3001-676X",
        "https://orcid.org/https://example.com/0000-0003-3001-676X",
        "0000-0003-3001-676x",
    ],
)
def test_get_author_by_orcid_normalizes(
    responses: RequestsMock, declared: str
) -> None:
    """Every declared ORCID form puts the bare identifier on the wire."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors",
        body="[]",
        content_type="application/json",
        status=200,
    )

    author_db = AuthorDb()
    author_db.get_author_by_orcid(declared)
    query = parse_qs(urlparse(responses.calls[0].request.url or "").query)
    assert query == {"orcid": ["0000-0003-3001-676X"]}
