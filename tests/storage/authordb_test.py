"""tests for the authordb storage module."""

from __future__ import annotations

import pytest_responses  # noqa: F401
from responses import RequestsMock

from documenteer.storage.authordb import AuthorDb


def test_from_yaml(responses: RequestsMock) -> None:
    # Assert that the AuthorDb object is created correctly
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
