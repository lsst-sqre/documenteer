"""Storage interface for lsst-texmf's authordb.yaml file."""

from __future__ import annotations

import requests
from pydantic import BaseModel, Field, HttpUrl, TypeAdapter

# normalize_orcid lives in documenteer.citations, which owns Documenteer's
# identifier normalizers, and is re-exported here so that the modules reaching
# for it alongside the author database keep importing it from this module.
from documenteer.citations import normalize_orcid

__all__ = [
    "Address",
    "Affiliation",
    "Author",
    "AuthorDb",
    "AuthorDbUnreachableError",
    "AuthorNotFoundError",
    "AuthorSearchResult",
    "InvalidOrcidError",
    "normalize_orcid",
]


class AuthorNotFoundError(ValueError):
    """Raised when an author ID is not present in the author database.

    This corresponds to an HTTP 404 response from the author API, as opposed
    to a transport failure (an unreachable database), which is signalled with
    an `AuthorDbUnreachableError`.
    """


class InvalidOrcidError(ValueError):
    """Raised when the author database rejects an ORCID as malformed.

    This corresponds to an HTTP 422 response from the author API. It is bad
    input rather than an unreachable database, so it is kept distinct from
    `AuthorDbUnreachableError`.
    """


class AuthorDbUnreachableError(ValueError):
    """Raised when the author database cannot be reached for resolution.

    This corresponds to a transport failure — a connection error, timeout,
    or a non-404 HTTP error (for example a 5xx) — as opposed to a definitive
    404 not-found response, which is signalled with an `AuthorNotFoundError`.
    """


class Address(BaseModel):
    """An address for an affiliation."""

    street: str | None = Field(
        default=None, description="Street address of the affiliation."
    )

    city: str | None = Field(
        default=None, description="City/town of the affiliation."
    )

    state: str | None = Field(
        default=None, description="State or province of the affiliation."
    )

    postal_code: str | None = Field(
        default=None, description="Postal code of the affiliation."
    )

    country: str | None = Field(
        default=None, description="Country of the affiliation."
    )


class Affiliation(BaseModel):
    """An affiliation."""

    name: str = Field(description="Name of the affiliation.")

    department: str | None = Field(
        default=None, description="Department within the organization."
    )

    internal_id: str = Field(
        description="Internal ID of the affiliation.",
    )

    ror: HttpUrl | None = Field(
        default=None,
        description="ROR URL of the affiliation.",
    )

    address: Address | None = Field(
        default=None, description="Address of the affiliation."
    )


class Author(BaseModel):
    """An author."""

    internal_id: str = Field(
        description="Internal ID of the author.",
    )

    family_name: str = Field(description="Family name of the author.")

    given_name: str | None = Field(
        description="Given name of the author.",
    )

    orcid: HttpUrl | None = Field(
        default=None,
        description="ORCID of the author (URL), or null if not available.",
    )

    notes: list[str] = Field(
        default_factory=list,
        description="Notes about the author.",
    )

    affiliations: list[Affiliation] = Field(
        default_factory=list,
        description="The author's affiliations.",
    )


class AuthorSearchResult(Author):
    """An author returned by a name search, with its relevance score."""

    score: float = Field(
        description=(
            "Relevance score (0-100) of the result for the search query. "
            "Ook documents 90-100 as an exact or near-exact match."
        ),
    )


_SEARCH_RESULTS_ADAPTER = TypeAdapter(list[AuthorSearchResult])
"""Validator for Ook's author-search response body."""

_AUTHORS_ADAPTER = TypeAdapter(list[Author])
"""Validator for Ook's ORCID-lookup response body, which carries no score."""


class AuthorDb:
    """An interface to Ook's author API."""

    def __init__(self) -> None: ...

    def search_authors(
        self, query: str, *, limit: int = 10
    ) -> list[AuthorSearchResult]:
        """Search the author database by name.

        Ook's author search is fuzzy and typo-tolerant, accepting names in
        several forms (``"Family, Given"``, ``"Given Family"``, a family name
        alone, and so on). Results are sorted by descending relevance score.

        Raises
        ------
        AuthorDbUnreachableError
            If the author database could not be searched, whether from a
            transport failure or any HTTP error status.
        """
        url = "https://roundtable.lsst.cloud/ook/authors"
        params = {"search": query, "limit": str(limit)}
        try:
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
        except requests.RequestException as e:
            raise AuthorDbUnreachableError(
                f"Failed to search authors for '{query}' at {url}"
            ) from e
        return _SEARCH_RESULTS_ADAPTER.validate_json(r.text)

    def get_author_by_orcid(self, orcid: str) -> Author | None:
        """Look an author up by ORCID, exactly.

        ORCID is the one globally unique, author-supplied identifier in this
        ecosystem, so this exact lookup succeeds where `search_authors`
        cannot — however differently the technote and the author database
        spell the name. ``orcid`` is reduced with `normalize_orcid` before
        it goes on the wire.

        The response is trusted only as far as the identifier it carries: a
        record counts as the answer when it declares the very ORCID that was
        asked for, never merely by being the first one listed. See the
        comment on the check itself for why that matters.

        Returns
        -------
        Author or None
            The author holding this ORCID, or `None` when the database
            returns no record that declares it. A miss is an ordinary
            outcome here, rather than the definitive 404 `get_author`
            reports.

        Raises
        ------
        InvalidOrcidError
            If the author database rejects the ORCID as malformed (422).
        AuthorDbUnreachableError
            If the author database could not be queried, whether from a
            transport failure or any other HTTP error status.
        """
        url = "https://roundtable.lsst.cloud/ook/authors"
        # normalize_orcid only returns None for a None input, which this
        # method's str parameter excludes.
        params = {"orcid": normalize_orcid(orcid) or orcid}
        try:
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 422:
                raise InvalidOrcidError(
                    f"The author database rejected ORCID '{orcid}' as "
                    f"malformed"
                ) from e
            raise AuthorDbUnreachableError(
                f"Failed to look up ORCID '{orcid}' at {url}"
            ) from e
        except requests.RequestException as e:
            raise AuthorDbUnreachableError(
                f"Failed to look up ORCID '{orcid}' at {url}"
            ) from e
        authors = _AUTHORS_ADAPTER.validate_json(r.text)
        # Match on the identifier rather than on the ordering. An author API
        # that does not recognize the `orcid` query parameter answers with an
        # ordinary author listing, which validates exactly as a filtered one
        # does, so `authors[0]` would be an arbitrary author reported as this
        # ORCID's owner — and a caller writes that ID into technote.toml.
        # Requiring the record to declare the ORCID closes that off whatever
        # the server does, and picks the right record out of a response that
        # carries several.
        requested = normalize_orcid(orcid)
        return next(
            (
                author
                for author in authors
                if normalize_orcid(author.orcid) == requested
            ),
            None,
        )

    def get_author(self, author_id: str) -> Author:
        """Get an author entry by ID."""
        url = f"https://roundtable.lsst.cloud/ook/authors/{author_id}"
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                raise AuthorNotFoundError(
                    f"Author {author_id} not found in the author database"
                ) from e
            raise AuthorDbUnreachableError(
                f"Failed to fetch author {author_id} from {url}"
            ) from e
        except requests.RequestException as e:
            raise AuthorDbUnreachableError(
                f"Failed to fetch author {author_id} from {url}"
            ) from e
        return Author.model_validate_json(r.text)
