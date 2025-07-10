"""A service for maintaining authors in a technote.toml file."""

from __future__ import annotations

from pathlib import Path

from documenteer.storage.authordb import Author, AuthorDb
from documenteer.storage.technotetoml import TechnoteTomlFile


class TechnoteAuthorService:
    """A service for maintaining authors in a technote.toml file."""

    def __init__(
        self, toml_file: TechnoteTomlFile, author_db: AuthorDb
    ) -> None:
        self.toml_file = toml_file
        self.author_db = author_db

    def write_toml(self, path: Path) -> None:
        """Write the technote.toml file."""
        self.toml_file.save(path)

    def add_author_by_id(self, author_id: str) -> Author:
        """Add an author to the technote.toml file."""
        author = self.author_db.get_author(author_id)

        self.toml_file.upsert_author(author)

        return author

    def sync_authors(self) -> list[Author]:
        """Synchronize author info from authordb.yaml."""
        updated_authors: list[Author] = []

        for author_id in self.toml_file.author_ids:
            author = self.author_db.get_author(author_id)
            updated_authors.append(author)
            self.toml_file.upsert_author(author)

        return updated_authors
