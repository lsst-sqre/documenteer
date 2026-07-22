"""Client for Ook's intersphinx inventory cache API."""

from __future__ import annotations

import os

import requests

from documenteer._requestsutils import requests_retry_session

__all__ = [
    "DEFAULT_BASE_URL",
    "TOKEN_ENV_VAR",
    "IntersphinxCacheClient",
    "IntersphinxCacheError",
    "IntersphinxCacheServerError",
    "IntersphinxCacheUnauthorizedError",
    "IntersphinxCacheUnreachableError",
]

DEFAULT_BASE_URL = "https://roundtable.lsst.cloud/ook"
"""Production base URL for the Ook API."""

TOKEN_ENV_VAR = "OOK_TOKEN"
"""Environment variable holding the bearer token for the Ook API."""


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

    def get_inventory(self, url: str) -> bytes:
        """Fetch the cached intersphinx inventory for an origin URL.

        Parameters
        ----------
        url
            The origin ``objects.inv`` URL to fetch from the cache, passed
            to the service as the ``url`` query parameter.

        Returns
        -------
        bytes
            The raw inventory bytes, returned unparsed for the caller to
            write to a local file.

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
        return r.content
