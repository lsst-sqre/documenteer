"""Tests for the documenteer.stoarge.technotetoml module."""

from __future__ import annotations

from typing import cast

import pytest_responses  # noqa: F401
import tomlkit
from responses import RequestsMock

from documenteer.storage.authordb import AuthorDb
from documenteer.storage.technotetoml import TechnoteTomlFile

BASIC_TECHNOTE_TOML = """
[technote]
title = "A Test Technote"
"""


def test_append_author(responses: RequestsMock) -> None:
    js_response_data = """
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
        body=js_response_data,
        content_type="application/json",
        status=200,
    )

    fe_response_data = """
{
    "affiliations": [
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
    "family_name": "Economou",
    "given_name": "Frossie",
    "internal_id": "economouf",
    "notes": [],
    "orcid": "https://orcid.org/0000-0002-8333-7615"
}
"""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/economouf",
        body=fe_response_data,
        content_type="application/json",
        status=200,
    )

    # Assert that the AuthorDb object is created correctly
    author_db = AuthorDb()
    author = author_db.get_author("sickj")

    technote = TechnoteTomlFile(BASIC_TECHNOTE_TOML)
    technote.upsert_author(author)
    print(technote.doc)

    authors_aot = technote.authors_aot
    a = authors_aot[0]
    name = cast("tomlkit.items.Table", a["name"])
    assert cast("str", name["given"]) == "Jonathan"
    assert cast("str", name["family"]) == "Sick"
    assert cast("str", a["internal_id"]) == "sickj"
    assert cast("str", a["orcid"]) == "https://orcid.org/0000-0003-3001-676X"
    affiliations_aot = cast("tomlkit.items.AoT", a["affiliations"])
    assert cast("str", affiliations_aot[1]["internal_id"]) == "RubinObs"

    # Modify that author and re-append. It should be modified since author_id
    # matches
    author.given_name = "Jon"
    technote.upsert_author(author)
    name = cast("tomlkit.items.Table", authors_aot[0]["name"])
    assert cast("str", name["given"]) == "Jon"

    # Append a different author
    author2 = author_db.get_author("economouf")
    technote.upsert_author(author2)
    name = cast("tomlkit.items.Table", authors_aot[1]["name"])
    assert cast("str", name["given"]) == "Frossie"
