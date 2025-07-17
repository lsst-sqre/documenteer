"""Tests for the documenteer.stoarge.technotetoml module."""

from __future__ import annotations

from typing import cast

import pytest_responses  # noqa: F401
import tomlkit
import tomlkit.items
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


def test_author_with_null_orcid(responses: RequestsMock) -> None:
    """Test handling of author with null ORCID."""
    author_response_data = """
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
    "family_name": "Smith",
    "given_name": "John",
    "internal_id": "smithj",
    "notes": [],
    "orcid": null
}
"""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/smithj",
        body=author_response_data,
        content_type="application/json",
        status=200,
    )

    author_db = AuthorDb()
    author = author_db.get_author("smithj")

    technote = TechnoteTomlFile(BASIC_TECHNOTE_TOML)
    technote.upsert_author(author)

    authors_aot = technote.authors_aot
    a = authors_aot[0]
    name = cast("tomlkit.items.Table", a["name"])
    assert cast("str", name["given"]) == "John"
    assert cast("str", name["family"]) == "Smith"
    assert cast("str", a["internal_id"]) == "smithj"
    # ORCID should not be present in the TOML when it's null
    assert "orcid" not in a


def test_author_with_null_given_name(responses: RequestsMock) -> None:
    """Test handling of author with null given name."""
    author_response_data = """
{
    "affiliations": [
        {
            "address": {
                "city": "Cambridge",
                "country": "USA",
                "postal_code": "02138",
                "state": "MA",
                "street": "1 Harvard Yard"
            },
            "department": null,
            "internal_id": "Harvard",
            "name": "Harvard University",
            "ror": "https://ror.org/03vek6s52"
        }
    ],
    "family_name": "Lastname",
    "given_name": null,
    "internal_id": "lastnamex",
    "notes": [],
    "orcid": "https://orcid.org/0000-0000-0000-0000"
}
"""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/lastnamex",
        body=author_response_data,
        content_type="application/json",
        status=200,
    )

    author_db = AuthorDb()
    author = author_db.get_author("lastnamex")

    technote = TechnoteTomlFile(BASIC_TECHNOTE_TOML)
    technote.upsert_author(author)

    authors_aot = technote.authors_aot
    a = authors_aot[0]
    name = cast("tomlkit.items.Table", a["name"])
    # Given name should not be present in the TOML when it's null
    assert "given" not in name
    assert cast("str", name["family"]) == "Lastname"
    assert cast("str", a["internal_id"]) == "lastnamex"
    assert cast("str", a["orcid"]) == "https://orcid.org/0000-0000-0000-0000"


def test_author_with_affiliation_null_ror(responses: RequestsMock) -> None:
    """Test handling of affiliation with null ROR."""
    author_response_data = """
{
    "affiliations": [
        {
            "address": {
                "city": "Small Town",
                "country": "USA",
                "postal_code": "12345",
                "state": "ST",
                "street": "123 Main St"
            },
            "department": "Engineering",
            "internal_id": "SmallOrg",
            "name": "Small Organization Inc.",
            "ror": null
        }
    ],
    "family_name": "Doe",
    "given_name": "Jane",
    "internal_id": "doej",
    "notes": [],
    "orcid": "https://orcid.org/0000-0000-0000-0001"
}
"""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/doej",
        body=author_response_data,
        content_type="application/json",
        status=200,
    )

    author_db = AuthorDb()
    author = author_db.get_author("doej")

    technote = TechnoteTomlFile(BASIC_TECHNOTE_TOML)
    technote.upsert_author(author)

    authors_aot = technote.authors_aot
    a = authors_aot[0]
    name = cast("tomlkit.items.Table", a["name"])
    assert cast("str", name["given"]) == "Jane"
    assert cast("str", name["family"]) == "Doe"
    assert cast("str", a["internal_id"]) == "doej"
    assert cast("str", a["orcid"]) == "https://orcid.org/0000-0000-0000-0001"

    affiliations_aot = cast("tomlkit.items.AoT", a["affiliations"])
    affiliation = affiliations_aot[0]
    assert cast("str", affiliation["name"]) == "Small Organization Inc."
    assert cast("str", affiliation["internal_id"]) == "SmallOrg"
    # ROR should not be present in the TOML when it's null
    assert "ror" not in affiliation


def test_author_with_multiple_null_fields(responses: RequestsMock) -> None:
    """Test handling of author with multiple null fields."""
    author_response_data = """
{
    "affiliations": [
        {
            "address": {
                "city": "Unknown City",
                "country": "Unknown Country",
                "postal_code": null,
                "state": null,
                "street": null
            },
            "department": null,
            "internal_id": "UnknownOrg",
            "name": "Unknown Organization",
            "ror": null
        }
    ],
    "family_name": "Anonymous",
    "given_name": null,
    "internal_id": "anon",
    "notes": [],
    "orcid": null
}
"""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/anon",
        body=author_response_data,
        content_type="application/json",
        status=200,
    )

    author_db = AuthorDb()
    author = author_db.get_author("anon")

    technote = TechnoteTomlFile(BASIC_TECHNOTE_TOML)
    technote.upsert_author(author)

    authors_aot = technote.authors_aot
    a = authors_aot[0]
    name = cast("tomlkit.items.Table", a["name"])
    # Given name should not be present when null
    assert "given" not in name
    assert cast("str", name["family"]) == "Anonymous"
    assert cast("str", a["internal_id"]) == "anon"
    # ORCID should not be present when null
    assert "orcid" not in a

    affiliations_aot = cast("tomlkit.items.AoT", a["affiliations"])
    affiliation = affiliations_aot[0]
    assert cast("str", affiliation["name"]) == "Unknown Organization"
    assert cast("str", affiliation["internal_id"]) == "UnknownOrg"
    # ROR should not be present when null
    assert "ror" not in affiliation
