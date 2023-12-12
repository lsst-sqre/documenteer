"""Test the TechnoteMigrationService class."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
import yaml

from documenteer.services.technotemigration import TechnoteMigrationService
from documenteer.storage.authordb import AuthorDb
from documenteer.storage.technotetoml import TechnoteTomlFile


@pytest.fixture
def author_db_yaml() -> str:
    """Return the path to a sample authordb.yaml file."""
    return (
        Path(__file__).parent.parent / "data" / "authordb.yaml"
    ).read_text()


def test_migration(tmp_path: Path, author_db_yaml: str) -> None:
    """Test migrating a technote."""
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

    author_db = AuthorDb.from_yaml(author_db_yaml)
    service = TechnoteMigrationService(tmp_path, author_db)
    service.migrate(author_ids=["sickj"])

    toml_path = tmp_path / "technote.toml"
    assert toml_path.exists()
    print(toml_path.read_text())

    toml_file = TechnoteTomlFile.open(toml_path)
    assert cast(str, toml_file.technote_table["id"]) == "SQR-065"
    assert cast(str, toml_file.technote_table["series_id"]) == "SQR"
    assert toml_file.author_ids == ["sickj"]

    print(content_path.read_text())

    # assert False
