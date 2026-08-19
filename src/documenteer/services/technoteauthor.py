"""A service for maintaining authors in a technote.toml file."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from documenteer.storage.authordb import (
    Author,
    AuthorDb,
    AuthorDbUnreachableError,
    AuthorNotFoundError,
    InvalidOrcidError,
)
from documenteer.storage.technotetoml import (
    TechnoteAuthorEntry,
    TechnoteTomlFile,
)

__all__ = ["AuthorSyncOutcome", "SyncAction", "TechnoteAuthorService"]


class SyncAction(StrEnum):
    """What synchronizing one ``[[technote.authors]]`` entry did to it."""

    synced = "synced"
    """The entry's ``internal_id`` resolved and its metadata was refreshed."""

    repaired = "repaired"
    """The entry's ``internal_id`` was wrong; its ORCID supplied the right
    one."""

    filled = "filled"
    """The entry declared no ``internal_id``; its ORCID supplied one."""

    skipped = "skipped"
    """The entry resolved to no author at all and was left as it was."""


@dataclass(frozen=True)
class AuthorSyncOutcome:
    """What `TechnoteAuthorService.sync_authors` did with one author entry."""

    action: SyncAction
    """What was done to the entry."""

    author: Author | None = None
    """The author database record written into the entry.

    `None` for a `SyncAction.skipped` entry, which is the one action that
    writes nothing.
    """

    previous_internal_id: str | None = None
    """The ``internal_id`` the entry declared before a `SyncAction.repaired`
    outcome rewrote it."""

    reason: str | None = None
    """Why a `SyncAction.skipped` entry could not be resolved, as a sentence
    fit to report to the user."""


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

    def add_author_by_orcid(self, orcid: str) -> Author:
        """Add an author to the technote.toml file by their ORCID.

        ORCID is globally unique and author-supplied, so a writer who knows
        an author's ORCID — from a paper, a profile page, or the author
        themselves — can add them without first hunting down their Rubin
        internal ID in authordb.yaml.

        Raises
        ------
        AuthorNotFoundError
            If no author in the Rubin author database holds this ORCID. The
            storage tier reports that miss as `None` rather than as an error,
            because a miss is an ordinary outcome of a query; adding an author
            who does not exist is not, so it is raised here.
        """
        author = self.author_db.get_author_by_orcid(orcid)
        if author is None:
            raise AuthorNotFoundError(
                f"No author in the Rubin author database has ORCID {orcid}"
            )

        self.toml_file.upsert_author(author)

        return author

    def sync_authors(self) -> list[AuthorSyncOutcome]:
        """Synchronize author info from the Rubin author database.

        Every ``[[technote.authors]]`` entry is resolved independently, in
        file order. An entry whose ``internal_id`` is wrong or missing is
        repaired from its declared ORCID, which is globally unique and so
        identifies the author exactly; an entry that resolves to no author at
        all is reported and left untouched rather than abandoning the whole
        run, so one bad entry no longer costs every other author their update.

        Returns
        -------
        list of AuthorSyncOutcome
            One outcome per entry, in file order. A caller should treat any
            `SyncAction.skipped` outcome as a failure of the run as a whole,
            even though the other entries were synchronized and written.
        """
        return [
            self._sync_entry(entry) for entry in self.toml_file.author_entries
        ]

    def _sync_entry(self, entry: TechnoteAuthorEntry) -> AuthorSyncOutcome:
        """Synchronize one author entry, repairing its ID where needed."""
        declared_id = entry.internal_id
        if declared_id is not None:
            try:
                author = self.author_db.get_author(declared_id)
            except AuthorNotFoundError:
                pass  # Fall through to the ORCID repair below.
            except AuthorDbUnreachableError as e:
                return _skip(entry, f"the lookup failed: {e}")
            else:
                entry.update(author)
                return AuthorSyncOutcome(SyncAction.synced, author=author)

        declared_orcid = entry.orcid
        if declared_orcid is None:
            return _skip(entry, _no_orcid_reason(declared_id))
        try:
            orcid_author = self.author_db.get_author_by_orcid(declared_orcid)
        except (AuthorDbUnreachableError, InvalidOrcidError) as e:
            return _skip(entry, f"the ORCID lookup failed: {e}")
        if orcid_author is None:
            return _skip(entry, _orcid_miss_reason(declared_id))

        entry.update(orcid_author)
        return AuthorSyncOutcome(
            SyncAction.repaired
            if declared_id is not None
            else SyncAction.filled,
            author=orcid_author,
            previous_internal_id=declared_id,
        )


def _skip(entry: TechnoteAuthorEntry, reason: str) -> AuthorSyncOutcome:
    """Report an entry that could not be resolved, leaving it untouched.

    The entry is named by the technote's own spelling of the author's name:
    an entry that resolves to nothing has no author database record to name
    it by, and the name is what the reader will look for in
    :file:`technote.toml`.
    """
    label = entry.name or entry.internal_id or "(unnamed)"
    return AuthorSyncOutcome(
        SyncAction.skipped,
        reason=f"Could not sync author {label}: {reason}",
    )


def _no_orcid_reason(declared_id: str | None) -> str:
    """Explain an entry with no ORCID to fall back on."""
    if declared_id is None:
        return "the entry declares neither an internal_id nor an ORCID."
    return (
        f"internal_id '{declared_id}' is not in the Rubin author database, "
        f"and the entry declares no ORCID to fall back on."
    )


def _orcid_miss_reason(declared_id: str | None) -> str:
    """Explain an entry whose declared ORCID resolves to nobody."""
    if declared_id is None:
        return (
            "the entry declares no internal_id, and its ORCID matches no "
            "entry in the Rubin author database."
        )
    return (
        f"neither internal_id '{declared_id}' nor its ORCID matches an entry "
        f"in the Rubin author database."
    )
