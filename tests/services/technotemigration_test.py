"""Test the TechnoteMigrationService class."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest_responses  # noqa: F401
import yaml
from responses import RequestsMock

from documenteer.services.technotemigration import TechnoteMigrationService
from documenteer.storage.authordb import AuthorDb
from documenteer.storage.technotetoml import TechnoteTomlFile


def test_migration(tmp_path: Path, responses: RequestsMock) -> None:
    """Test migrating a technote."""
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
    metadata = {
        "series": "SQR",
        "serial_number": "065",
        "doc_title": "Design of Noteburst",
        "description": "Hello world.",
        "github_url": "https://github.com/lsst-sqre/sqr-065",
    }

    content = """
:tocdepth: 1

.. Please do not modify tocdepth.

.. sectnum::

Introduction
============

Hello

.. rubric:: References

.. bibliography:: local.bib lsstbib/books.bib
   :style: lsst_aa
"""

    metadata_path = tmp_path / "metadata.yaml"
    metadata_path.write_text(yaml.dump(metadata))

    content_path = tmp_path / "index.rst"
    content_path.write_text(content)

    author_db = AuthorDb()
    service = TechnoteMigrationService(tmp_path, author_db)
    service.migrate(author_ids=["sickj"])

    toml_path = tmp_path / "technote.toml"
    assert toml_path.exists()

    toml_file = TechnoteTomlFile.open(toml_path)
    assert cast("str", toml_file.technote_table["id"]) == "SQR-065"
    assert cast("str", toml_file.technote_table["series_id"]) == "SQR"
    assert toml_file.author_ids == ["sickj"]
