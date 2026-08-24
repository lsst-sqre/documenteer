"""Client for the metadata DataCite has registered for a DOI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self

import requests
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from documenteer.citations import normalize_doi

__all__ = [
    "DATACITE_API_ROOT",
    "DATACITE_TIMEOUT",
    "DataCiteClient",
    "DataCiteRecord",
    "DataCiteUnavailableError",
    "datacite_api_url",
]

DATACITE_API_ROOT = "https://api.datacite.org/dois/"
"""Root of DataCite's public DOI metadata API.

The API needs no credentials for a read, and answers with the metadata the
DOI's registrant deposited — for a Rubin technote, what Ook registered when
the DOI was minted.
"""

DATACITE_TIMEOUT = 5.0
"""Seconds to wait for DataCite, deliberately short.

The only caller is a lint rule that degrades to silence when DataCite does
not answer, so waiting longer buys nothing: it would only stall a lint run
(or the CI job around it) that is going to reach the same conclusion either
way.
"""


def datacite_api_url(doi: str) -> str:
    """Address a DOI's registered metadata in DataCite's API.

    Parameters
    ----------
    doi
        A DOI in any of the spellings `~documenteer.citations.normalize_doi`
        accepts.

    Returns
    -------
    str
        The API URL the DOI's registered metadata is read from. A DOI's
        suffix may itself contain slashes, which DataCite accepts unescaped
        in the path.

    Raises
    ------
    ValueError
        Raised if the value is not a syntactically-valid DOI.
    """
    return f"{DATACITE_API_ROOT}{normalize_doi(doi)}"


class DataCiteUnavailableError(ValueError):
    """Raised when DataCite could not be asked what a DOI is registered as.

    This covers every outcome that leaves the registered metadata *unknown* —
    a connection failure, a timeout, an HTTP error other than 404, and a
    response body that is not a DOI record — as opposed to the definitive
    "this DOI is not registered", which `DataCiteClient.get_record` reports by
    returning `None`.
    """


class _Title(BaseModel):
    """One entry of a DOI record's ``titles`` list."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    title: str | None = None

    title_type: str | None = Field(default=None, alias="titleType")
    """The kind of title this is.

    DataCite gives the title *of the work* no ``titleType``; a subtitle,
    translated title, or other alternative carries one.
    """


class _Creator(BaseModel):
    """One entry of a DOI record's ``creators`` list."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    name: str | None = None

    given_name: str | None = Field(default=None, alias="givenName")

    family_name: str | None = Field(default=None, alias="familyName")

    @property
    def display_name(self) -> str | None:
        """The creator's name, however the record spells it.

        DataCite's ``name`` is the authoritative display form and carries an
        organizational creator's whole name, so it is preferred. A record that
        deposited only the parts is assembled into the same ``Family, Given``
        form a citation uses.
        """
        if self.name:
            return self.name
        if self.family_name and self.given_name:
            return f"{self.family_name}, {self.given_name}"
        return self.family_name or self.given_name


class _Attributes(BaseModel):
    """The subset of a DOI record's attributes this client reads."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    doi: str | None = None

    titles: list[_Title] = Field(default_factory=list)

    creators: list[_Creator] = Field(default_factory=list)


class _Data(BaseModel):
    """The JSON:API ``data`` member of a DOI response."""

    model_config = ConfigDict(extra="ignore")

    attributes: _Attributes


class _DoiResponse(BaseModel):
    """A DataCite ``/dois/{id}`` response."""

    model_config = ConfigDict(extra="ignore")

    data: _Data


@dataclass(frozen=True)
class DataCiteRecord:
    """The registered metadata for one DOI.

    Only the fields a citation is compared on are carried; the rest of a DOI
    record is ignored, so a DataCite schema addition cannot break a read.
    """

    doi: str
    """The DOI, in the bare ``10.NNNN/suffix`` form."""

    title: str | None
    """The registered title of the work, if it declares one."""

    creator_names: tuple[str, ...]
    """The registered creators, in the order DataCite lists them."""

    url: str
    """The API URL this metadata was read from."""

    @classmethod
    def from_json(cls, *, doi: str, url: str, text: str) -> Self:
        """Build a record from a DataCite response body.

        Raises
        ------
        DataCiteUnavailableError
            Raised if the body is not a DOI record. An answer that cannot be
            read leaves the registered metadata as unknown as a connection
            failure does, so it is reported the same way.
        """
        try:
            payload = _DoiResponse.model_validate_json(text)
        except ValidationError as e:
            raise DataCiteUnavailableError(
                f"DataCite's response for DOI {doi} at {url} is not a DOI "
                f"record"
            ) from e
        attributes = payload.data.attributes
        return cls(
            doi=attributes.doi or doi,
            title=_main_title(attributes.titles),
            creator_names=tuple(
                name
                for creator in attributes.creators
                if (name := creator.display_name)
            ),
            url=url,
        )


class DataCiteClient:
    """Reads the metadata registered for a DOI from DataCite's public API.

    Parameters
    ----------
    timeout
        Seconds to wait for DataCite. The default is deliberately short; see
        `DATACITE_TIMEOUT`.
    """

    def __init__(self, *, timeout: float = DATACITE_TIMEOUT) -> None:
        self._timeout = timeout

    def get_record(self, doi: str) -> DataCiteRecord | None:
        """Fetch the metadata registered for a DOI.

        Parameters
        ----------
        doi
            A DOI in any of the spellings
            `~documenteer.citations.normalize_doi` accepts.

        Returns
        -------
        `DataCiteRecord` or None
            The registered metadata, or `None` when DataCite answers that the
            DOI is not registered (404). A DOI that has been reserved but not
            yet made findable is an ordinary outcome rather than a failure,
            which is why it is a value rather than an exception.

        Raises
        ------
        ValueError
            Raised if the value is not a syntactically-valid DOI. Nothing is
            requested in that case.
        DataCiteUnavailableError
            Raised when the registered metadata could not be read at all —
            a transport failure, a timeout, an HTTP error other than 404, or
            a response that is not a DOI record.
        """
        url = datacite_api_url(doi)
        try:
            r = requests.get(
                url,
                headers={"Accept": "application/vnd.api+json"},
                timeout=self._timeout,
            )
            r.raise_for_status()
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            raise DataCiteUnavailableError(
                f"Failed to fetch the metadata registered for DOI {doi} "
                f"from {url}"
            ) from e
        except requests.RequestException as e:
            raise DataCiteUnavailableError(
                f"Failed to fetch the metadata registered for DOI {doi} "
                f"from {url}"
            ) from e
        return DataCiteRecord.from_json(
            doi=normalize_doi(doi), url=url, text=r.text
        )


def _main_title(titles: list[_Title]) -> str | None:
    """Pick the title *of the work* out of a record's titles.

    A record may list a subtitle or a translated title alongside the title of
    the work, each marked with a ``titleType``; the untyped one is the title
    itself. A record that types every title it has is read for its first
    title rather than reported as untitled.
    """
    typed_fallback: str | None = None
    for entry in titles:
        if not entry.title:
            continue
        if entry.title_type is None:
            return entry.title
        if typed_fallback is None:
            typed_fallback = entry.title
    return typed_fallback
