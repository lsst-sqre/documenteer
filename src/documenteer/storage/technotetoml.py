"""Interface to a technote.toml file for a technote."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Self, cast

import tomlkit

from .authordb import Affiliation, Author

__all__ = ["TechnoteAuthorEntry", "TechnoteTomlFile"]


class TechnoteAuthorEntry:
    """A handle on one ``[[technote.authors]]`` table.

    The handle keeps hold of the table it was made from, so a caller can
    rewrite *that* entry — including its ``internal_id`` — without having to
    find it in the array of tables again. That matters because
    `TechnoteTomlFile.upsert_author` matches on ``internal_id``: writing a
    *corrected* ID through it would fail to match the entry it corrects and
    append a duplicate instead.

    Parameters
    ----------
    table
        The ``[[technote.authors]]`` table this handle wraps.
    """

    def __init__(self, table: tomlkit.items.Table) -> None:
        self._table = table

    @property
    def name(self) -> str:
        """The technote's own spelling of the author's name.

        This is how the *technote* names the author, not how the author
        database does. It is what identifies an entry to a reader of
        :file:`technote.toml`, and so the only useful way to report on an
        entry that cannot be resolved against the database at all.
        """
        name = self._table.get("name")
        if name is None:
            return ""
        given = name.get("given")
        family = name.get("family")
        return " ".join(str(part) for part in (given, family) if part)

    @property
    def internal_id(self) -> str | None:
        """The declared ``internal_id``, or `None` if the entry has none."""
        value = self._table.get("internal_id")
        return None if value is None else str(value)

    @property
    def orcid(self) -> str | None:
        """The declared ``orcid``, or `None` if the entry has none."""
        value = self._table.get("orcid")
        return None if value is None else str(value)

    def update(self, author: Author) -> None:
        """Rewrite this entry from an author database record."""
        _update_author_table(self._table, author)


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

    @property
    def data(self) -> dict[str, Any]:
        """The file's content as plain Python data.

        Every tomlkit item carries its own formatting — the whitespace and
        comments around it — which is what makes an *edit* preserve the rest
        of the file, and what gets in the way of simply *reading* a value.
        Unwrapping yields ordinary dicts, lists, strings, and
        `~datetime.date` objects instead, so a consumer that only reads
        technote.toml (such as CITATION.cff generation) never has to reason
        about tomlkit's types.
        """
        return self._doc.unwrap()

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
        return cast("tomlkit.items.Table", self._doc["technote"])

    @property
    def authors_aot(self) -> tomlkit.items.AoT:
        """The authors array of tables."""
        if "authors" not in self.technote_table:
            self.technote_table["authors"] = tomlkit.aot()
        return cast("tomlkit.items.AoT", self.technote_table["authors"])

    @property
    def author_entries(self) -> list[TechnoteAuthorEntry]:
        """A handle on each ``[[technote.authors]]`` table, in file order.

        Every entry is listed, including one that declares no
        ``internal_id`` — those are exactly the entries a caller may want to
        repair.
        """
        if "authors" not in self.technote_table:
            return []
        return [TechnoteAuthorEntry(table) for table in self.authors_aot]

    @property
    def author_ids(self) -> list[str]:
        """A list of author IDs (keys in authordb.yaml).

        Authors without an ``internal_id`` are not included.
        """
        return [
            entry.internal_id
            for entry in self.author_entries
            if entry.internal_id is not None
        ]

    def upsert_author(self, author: Author) -> None:
        """Append an author to the technote.toml file, or update in place."""
        for entry in self.author_entries:
            if entry.internal_id == author.internal_id:
                entry.update(author)
                return

        # Append a new author
        t = tomlkit.table()
        _update_author_table(t, author)
        self.authors_aot.append(t)


def _update_author_table(table: tomlkit.items.Table, author: Author) -> None:
    """Update a toml author table with the Author data."""
    name_table = tomlkit.inline_table()
    if author.given_name is not None:
        name_table["given"] = author.given_name
    if author.family_name is not None:
        name_table["family"] = author.family_name

    table["name"] = name_table

    table["internal_id"] = author.internal_id

    if author.orcid is not None:
        table["orcid"] = str(author.orcid)

    if "affiliations" not in table:
        table.add("affiliations", tomlkit.aot())
    affiliations_aot = cast("tomlkit.items.AoT", table["affiliations"])

    existing_affiliation_ids = [
        a["internal_id"] for a in affiliations_aot if "internal_id" in a
    ]

    for affiliation in author.affiliations:
        if affiliation.internal_id not in existing_affiliation_ids:
            # Add a new affiliation
            new_affiliation_table = tomlkit.table()
            _update_affiliation_table(new_affiliation_table, affiliation)
            affiliations_aot.append(new_affiliation_table)
        else:
            # Update existing affiliation
            for t in affiliations_aot:
                # A hand-written affiliation table may declare no
                # internal_id; it can never match, so skip rather than
                # raise NonExistentKey.
                if t.get("internal_id") == affiliation.internal_id:
                    _update_affiliation_table(t, affiliation)
                    break


def _update_affiliation_table(
    t: tomlkit.items.Table, affiliation_info: Affiliation
) -> None:
    """Update a toml affiliation table with the Affiliation data."""
    t["name"] = affiliation_info.name
    t["internal_id"] = affiliation_info.internal_id
    if affiliation_info.ror is not None:
        t["ror"] = str(affiliation_info.ror)
