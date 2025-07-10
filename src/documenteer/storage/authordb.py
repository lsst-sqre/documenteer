"""Storage interface for lsst-texmf's authordb.yaml file."""

from __future__ import annotations

import requests
from pydantic import BaseModel, Field, HttpUrl

__all__ = ["AuthorDb", "Author", "Affiliation", "Address"]


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


class AuthorDb:
    """An interface to Ook's author API."""

    def __init__(self) -> None: ...

    def get_author(self, author_id: str) -> Author:
        """Get an author entry by ID."""
        url = f"https://roundtable.lsst.cloud/ook/authors/{author_id}"
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
        except requests.RequestException as e:
            raise ValueError(
                f"Failed to fetch author {author_id} from {url}"
            ) from e
        return Author.model_validate_json(r.text)
