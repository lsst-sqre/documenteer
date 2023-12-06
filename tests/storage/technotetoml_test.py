"""Tests for the documenteer.stoarge.technotetoml module."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
import tomlkit

from documenteer.storage.authordb import AuthorDb
from documenteer.storage.technotetoml import TechnoteTomlFile

BASIC_TECHNOTE_TOML = """
[technote]
title = "A Test Technote"
"""


@pytest.fixture
def author_db_yaml() -> str:
    """Return the path to a sample authordb.yaml file."""
    return (
        Path(__file__).parent.parent / "data" / "authordb.yaml"
    ).read_text()


def test_append_author(author_db_yaml: str) -> None:
    author_db = AuthorDb.from_yaml(author_db_yaml)

    # Assert that the AuthorDb object is created correctly
    author = author_db.get_author("sickj")

    technote = TechnoteTomlFile(BASIC_TECHNOTE_TOML)
    technote.upsert_author(author)
    print(technote.doc)

    authors_aot = technote.authors_aot
    # a = cast(tomlkit.items.Table, authors_aot[0])
    a = authors_aot[0]
    assert cast(str, a["given"]) == "Jonathan"
    assert cast(str, a["family"]) == "Sick"
    assert cast(str, a["internal_id"]) == "sickj"
    assert cast(str, a["orcid"]) == "https://orcid.org/0000-0003-3001-676X"
    affiliations_aot = cast(tomlkit.items.AoT, a["affiliations"])
    assert cast(str, affiliations_aot[0]["internal_id"]) == "RubinObs"

    # Modify that author and re-append. It should be modified since author_id
    # matches
    author.given_name = "Jon"
    technote.upsert_author(author)
    assert cast(str, authors_aot[0]["given"]) == "Jon"

    # Append a different author
    author2 = author_db.get_author("economouf")
    technote.upsert_author(author2)
    assert cast(str, authors_aot[1]["given"]) == "Frossie"
