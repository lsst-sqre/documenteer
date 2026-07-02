"""tests for the authordb storage module."""

from __future__ import annotations

import pytest
import pytest_responses  # noqa: F401
import requests
from responses import RequestsMock

from documenteer.storage.authordb import AuthorDb, AuthorNotFoundError


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
    """A transport failure raises a plain ``ValueError``, not a not-found."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/sickj",
        body=requests.ConnectionError("connection refused"),
    )

    author_db = AuthorDb()
    with pytest.raises(ValueError, match="Failed to fetch author") as exc_info:
        author_db.get_author("sickj")
    assert not isinstance(exc_info.value, AuthorNotFoundError)


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
    assert not isinstance(exc_info.value, AuthorNotFoundError)
