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

AUTHOR_RESPONSE = """
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

LEGACY_CONTENT = """
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


def migrate_legacy_technote(
    tmp_path: Path, responses: RequestsMock
) -> TechnoteMigrationService:
    """Set up a legacy technote in ``tmp_path`` and migrate it."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/sickj",
        body=AUTHOR_RESPONSE,
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
    (tmp_path / "metadata.yaml").write_text(yaml.dump(metadata))
    (tmp_path / "index.rst").write_text(LEGACY_CONTENT)

    author_db = AuthorDb()
    service = TechnoteMigrationService(tmp_path, author_db)
    service.migrate(author_ids=["sickj"])
    return service


def test_migration(tmp_path: Path, responses: RequestsMock) -> None:
    """Test migrating a technote."""
    migrate_legacy_technote(tmp_path, responses)

    toml_path = tmp_path / "technote.toml"
    assert toml_path.exists()

    toml_file = TechnoteTomlFile.open(toml_path)
    assert cast("str", toml_file.technote_table["id"]) == "SQR-065"
    assert cast("str", toml_file.technote_table["series_id"]) == "SQR"
    assert toml_file.author_ids == ["sickj"]


def test_migration_writes_tooling(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A migrated technote can run every Documenteer command it is told to."""
    migrate_legacy_technote(tmp_path, responses)

    requirements = (tmp_path / "requirements.txt").read_text()
    assert requirements.strip() == "documenteer[technote]>=2.5.0,<3"

    tox_ini = (tmp_path / "tox.ini").read_text()
    assert "[testenv:sync-authors]" in tox_ini
    assert "documenteer technote sync-authors" in tox_ini
    assert "[testenv:sync-cff]" in tox_ini
    assert "documenteer technote sync-cff" in tox_ini
    assert "[testenv:technote-lint]" in tox_ini
    assert "documenteer technote lint" in tox_ini

    makefile = (tmp_path / "Makefile").read_text()
    assert "sync-authors:\n\ttox run -e sync-authors" in makefile
    assert "sync-cff:\n\ttox run -e sync-cff" in makefile
    assert "tox run -e lint,technote-lint,linkcheck" in makefile
