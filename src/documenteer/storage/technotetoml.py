"""Interface to a technote.toml file for a technote."""

from __future__ import annotations

from pathlib import Path
from typing import Self, cast

import tomlkit

from .authordb import Affiliation, Author

__all__ = ["TechnoteTomlFile"]


class TechnoteTomlFile:
    """An editable technote.toml file.

    To create this class from a file `~pathlib.Path`, using the `open` class
    method.

    Parameters
    ----------
    content
        The text content of the technote.toml file.
    """

    def __init__(self, content: str) -> None:
        self._doc = tomlkit.parse(content)

    @property
    def doc(self) -> tomlkit.TOMLDocument:
        """The editable tomlkit document."""
        return self._doc

    @classmethod
    def open(cls, path: Path) -> Self:
        """Open a technote.toml file from the given path.

        Parameters
        ----------
        path
            The path to the technote.toml file.

        Returns
        -------
        `TechnoteTomlFile`
            The technote.toml file object.
        """
        text = path.read_text()
        return cls(text)

    def save(self, path: Path) -> None:
        """Write the technote.toml file to the given path."""
        path.write_text(tomlkit.dumps(self._doc))

    @property
    def technote_table(self) -> tomlkit.items.Table:
        """The technote table."""
        if "technote" not in self._doc:
            self._doc["technote"] = tomlkit.table()
        return cast(tomlkit.items.Table, self._doc["technote"])

    @property
    def authors_aot(self) -> tomlkit.items.AoT:
        """The authors array of tables."""
        if "authors" not in self.technote_table:
            self.technote_table["authors"] = tomlkit.aot()
        return cast(tomlkit.items.AoT, self.technote_table["authors"])

    @property
    def author_ids(self) -> list[str]:
        """A list of author IDs (keys in authordb.yaml).

        Authors without an ``internal_id`` are not included.
        """
        if "authors" not in self.technote_table:
            return []
        return [
            a["internal_id"] for a in self.authors_aot if "internal_id" in a
        ]

    def upsert_author(self, author: Author) -> None:
        """Append an author to the technote.toml file, or update in place."""
        # Check if the author already exists
        author_exists = False

        for existing_author in self.authors_aot:
            if (
                "internal_id" in existing_author
                and existing_author["internal_id"] == author.internal_id
            ):
                author_exists = True
                # Write over the existing author
                self._update_author(existing_author, author)
                break

        if not author_exists:
            # Append a new author
            t = tomlkit.table()
            self._update_author(t, author)
            self.authors_aot.append(t)

    def _update_author(
        self, table: tomlkit.items.Table, author: Author
    ) -> None:
        """Update a toml author table with the Author data."""
        name_table = tomlkit.inline_table()
        name_table["given"] = author.given_name
        name_table["family"] = author.family_name
        table["name"] = name_table
        table["internal_id"] = author.internal_id
        if author.orcid is not None:
            table["orcid"] = str(author.orcid)

        if "affiliations" not in table:
            table.add("affiliations", tomlkit.aot())
        affiliations_aot = cast(tomlkit.items.AoT, table["affiliations"])
        existing_affiliation_ids = [a["internal_id"] for a in affiliations_aot]
        for affiliation in author.affiliations:
            if affiliation.internal_id not in existing_affiliation_ids:
                # Add a new affiliation
                new_affiliation_table = tomlkit.table()
                self._update_affiliation(new_affiliation_table, affiliation)
                affiliations_aot.append(new_affiliation_table)
            else:
                # Update existing affiliation
                for t in affiliations_aot:
                    if t["internal_id"] == affiliation.internal_id:
                        self._update_affiliation(t, affiliation)
                        break

    def _update_affiliation(
        self, t: tomlkit.items.Table, affiliation_info: Affiliation
    ) -> None:
        t["name"] = affiliation_info.name
        t["internal_id"] = affiliation_info.internal_id
        t["ror"] = str(affiliation_info.ror)
