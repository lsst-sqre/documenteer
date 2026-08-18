"""Client for Ook's intersphinx inventory cache API."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime

import requests

from documenteer._requestsutils import requests_retry_session

__all__ = [
    "CACHE_STATUS_HEADER",
    "DATE_FETCHED_HEADER",
    "DEFAULT_BASE_URL",
    "TOKEN_ENV_VAR",
    "IntersphinxCacheClient",
    "IntersphinxCacheError",
    "IntersphinxCacheServerError",
    "IntersphinxCacheUnauthorizedError",
    "IntersphinxCacheUnreachableError",
    "InventoryFetchResult",
]

DEFAULT_BASE_URL = "https://roundtable.lsst.cloud/ook"
"""Production base URL for the Ook API."""

TOKEN_ENV_VAR = "OOK_TOKEN"
"""Environment variable holding the bearer token for the Ook API."""

CACHE_STATUS_HEADER = "X-Ook-Inventory-Cache-Status"
"""Response header carrying how Ook served the inventory (e.g. ``hit``,
``stale``, ``miss``). Sent on both ``200`` and ``304`` responses."""

DATE_FETCHED_HEADER = "X-Ook-Inventory-Date-Fetched"
"""Response header carrying the RFC 3339 UTC time when Ook last confirmed the
inventory with its origin. Sent on both ``200`` and ``304`` responses.

Unlike the standard ``Age`` header, which rides the ``200`` alone, this header
also rides the ``304`` — so for a client that holds current bytes and only ever
revalidates, it is the only freshness signal it ever sees.
"""


def _parse_date_fetched(value: str | None) -> datetime | None:
    """Parse the `DATE_FETCHED_HEADER` value into an aware datetime.

    A missing header yields `None`, and so does a value that cannot be
    parsed: a header Ook gets wrong must never be able to fail a
    documentation build. A value carrying no UTC offset is read as UTC (Ook
    sends UTC) rather than left naive, so comparing it with the build
    machine's clock cannot raise either.
    """
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


@dataclass(frozen=True)
class InventoryFetchResult:
    """The outcome of a (possibly conditional) inventory fetch.

    A ``304 Not Modified`` response is signaled by ``not_modified`` being
    `True` with ``content`` `None`; a ``200 OK`` carries the fetched bytes in
    ``content`` with ``not_modified`` `False`. ``etag`` is the entity tag the
    caller should persist alongside the inventory: on a 200 it is the ETag
    from the response (or `None` when the server sent no ``ETag`` header), and
    on a 304 it is the ETag that was revalidated.
    """

    not_modified: bool
    """Whether the server reported the inventory unchanged (HTTP 304)."""

    content: bytes | None
    """The raw inventory bytes on a 200, or `None` on a 304."""

    etag: str | None
    """The entity tag to persist, or `None` when the server sent none."""

    cache_status: str | None = None
    """How Ook served the inventory, from `CACHE_STATUS_HEADER`, or `None`
    when the response carried no such header.

    Carried as a plain string rather than an enum so a value Ook adds later
    reaches the build-log summary verbatim instead of being silently dropped.
    """

    date_fetched: datetime | None = None
    """When Ook last *confirmed* the inventory with its origin, from
    `DATE_FETCHED_HEADER`, or `None` when the response carried no such header
    or the header could not be parsed.

    This is not when the served bytes were downloaded: a background refresh
    that the origin answered ``304 Not Modified`` keeps the stored bytes and
    still advances this anchor.
    """


class IntersphinxCacheError(ValueError):
    """An error interacting with Ook's intersphinx inventory cache."""


class IntersphinxCacheUnreachableError(IntersphinxCacheError):
    """The Ook intersphinx inventory cache could not be reached.

    Raised for a connection error or a request timeout. The extension maps
    this to leaving the mapping entry untouched so stock intersphinx fetches
    the origin directly.
    """


class IntersphinxCacheUnauthorizedError(IntersphinxCacheError):
    """The request to the Ook intersphinx inventory cache was not authorized.

    Raised when no ``OOK_TOKEN`` is available or the service rejects the
    token (HTTP 401/403).
    """


class IntersphinxCacheServerError(IntersphinxCacheError):
    """The Ook intersphinx inventory cache returned a server error.

    Raised for an HTTP 5xx response, including Ook's 502 for a cold miss
    when the origin is down.
    """


class IntersphinxCacheClient:
    """A client for Ook's intersphinx inventory cache API.

    The client fetches cached intersphinx object inventories from Ook so a
    documentation build no longer depends on the third-party origin site
    being reachable at build time.

    Parameters
    ----------
    base_url
        Base URL of the Ook API. Defaults to the production Ook API,
        `DEFAULT_BASE_URL`.
    token
        Bearer token for the Ook API. If not provided, the token is read
        from the ``OOK_TOKEN`` environment variable.
    session
        An existing requests session to use. By default a session with
        retries is created with
        `documenteer._requestsutils.requests_retry_session`.
    """

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        token: str | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token if token is not None else os.getenv(TOKEN_ENV_VAR)
        self._session = (
            session if session is not None else requests_retry_session()
        )

    def get_inventory(
        self, url: str, *, etag: str | None = None
    ) -> InventoryFetchResult:
        """Fetch the cached intersphinx inventory for an origin URL.

        Parameters
        ----------
        url
            The origin ``objects.inv`` URL to fetch from the cache, passed
            to the service as the ``url`` query parameter.
        etag
            An entity tag from a previously cached copy. When provided, the
            request carries an ``If-None-Match`` header so an unchanged
            inventory can be answered with ``304 Not Modified`` and no body.

        Returns
        -------
        InventoryFetchResult
            The fetch outcome: either new bytes plus the response ETag
            (``not_modified=False``), or a not-modified signal that echoes the
            revalidated ``etag`` (``not_modified=True``, ``content=None``).
            Either way, ``cache_status`` carries Ook's
            `CACHE_STATUS_HEADER` value and ``date_fetched`` its
            `DATE_FETCHED_HEADER` value, when the response sent them.

        Raises
        ------
        IntersphinxCacheUnauthorizedError
            Raised if no ``OOK_TOKEN`` is available, or the service rejects
            the token (HTTP 401/403).
        IntersphinxCacheUnreachableError
            Raised if the service cannot be reached (connection error or
            timeout).
        IntersphinxCacheServerError
            Raised if the service returns a server error (HTTP 5xx),
            including Ook's 502 for a cold miss with the origin down.
        IntersphinxCacheError
            Raised for any other non-2xx response.
        """
        if not self._token:
            raise IntersphinxCacheUnauthorizedError(
                "No Ook API token is available. Set the "
                f"{TOKEN_ENV_VAR} environment variable."
            )
        api_url = f"{self._base_url}/intersphinx/inventory"
        headers = {"Authorization": f"Bearer {self._token}"}
        if etag is not None:
            # Conditional revalidation: an unchanged inventory is answered
            # with 304 and transfers no body.
            headers["If-None-Match"] = etag
        try:
            r = self._session.get(
                api_url,
                headers=headers,
                params={"url": url},
                timeout=30.0,
            )
        except requests.exceptions.RetryError as e:
            # Retries were exhausted against a retryable 5xx status
            # (``requests_retry_session`` force-lists 500/502/504), so the
            # server error persisted rather than the service being
            # unreachable.
            raise IntersphinxCacheServerError(
                f"Server error from the Ook intersphinx inventory cache at "
                f"{api_url} for {url} after exhausting retries: {e}"
            ) from e
        except requests.RequestException as e:
            raise IntersphinxCacheUnreachableError(
                f"Could not reach the Ook intersphinx inventory cache at "
                f"{api_url} for {url}: {e}"
            ) from e
        if r.status_code in (401, 403):
            raise IntersphinxCacheUnauthorizedError(
                f"Not authorized to access the Ook intersphinx inventory "
                f"cache at {api_url} (HTTP {r.status_code}). Check the "
                f"{TOKEN_ENV_VAR} environment variable."
            )
        if r.status_code == 304:
            # The conditional request matched: the inventory is unchanged, so
            # the caller keeps its on-disk copy. Echo back the ETag it
            # revalidated with.
            return InventoryFetchResult(
                not_modified=True,
                content=None,
                etag=etag,
                cache_status=r.headers.get(CACHE_STATUS_HEADER),
                date_fetched=_parse_date_fetched(
                    r.headers.get(DATE_FETCHED_HEADER)
                ),
            )
        if r.status_code >= 500:
            raise IntersphinxCacheServerError(
                f"Server error from the Ook intersphinx inventory cache at "
                f"{api_url} for {url} (HTTP {r.status_code})."
            )
        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            # Any other non-2xx response lands here, including a 404 when the
            # inventory endpoint is not yet deployed. The extension treats
            # every IntersphinxCacheError the same way — leave the entry
            # untouched and fall back to a direct origin fetch — so no
            # dedicated error class is needed for the 404 case.
            raise IntersphinxCacheError(
                f"Error from the Ook intersphinx inventory cache at "
                f"{api_url} for {url}: {e}"
            ) from e
        return InventoryFetchResult(
            not_modified=False,
            content=r.content,
            etag=r.headers.get("ETag"),
            cache_status=r.headers.get(CACHE_STATUS_HEADER),
            date_fetched=_parse_date_fetched(
                r.headers.get(DATE_FETCHED_HEADER)
            ),
        )
