"""A service for maintaining authors in a technote.toml file."""

from __future__ import annotations

from pathlib import Path

from documenteer.storage.authordb import AuthorDb, AuthorInfo
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

    def add_author_by_id(self, author_id: str) -> AuthorInfo:
        """Add an author to the technote.toml file."""
        try:
            author = self.author_db.get_author(author_id)
        except KeyError:
            raise ValueError(f"Author {author_id} not found in authordb.yaml")

        self.toml_file.upsert_author(author)

        return author

    def sync_authors(self) -> list[AuthorInfo]:
        """Synchronize author info from authordb.yaml."""
        updated_authors: list[AuthorInfo] = []

        for author_id in self.toml_file.author_ids:
            try:
                author = self.author_db.get_author(author_id)
                updated_authors.append(author)
            except KeyError:
                raise ValueError(
                    f"Author {author_id} not found in authordb.yaml"
                )
            self.toml_file.upsert_author(author)

        return updated_authors
