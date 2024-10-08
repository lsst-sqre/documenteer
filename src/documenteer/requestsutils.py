"""Utilities for working with requests."""

__all__ = ("requests_retry_session",)

from collections.abc import Sequence

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry


def requests_retry_session(
    retries: int = 3,
    backoff_factor: float = 0.3,
    status_forcelist: Sequence[int] = (500, 502, 504),
    session: requests.Session | None = None,
) -> requests.Session:
    """Create a requests session that handles errors by retrying.

    Parameters
    ----------
    retries : `int`, optional
        Number of retries to attempt.
    backoff_factor : `float`, optional
        Backoff factor.
    status_forcelist : sequence of `str`, optional
        Status codes that must be retried.
    session : `requests.Session`
        An existing requests session to configure.

    Returns
    -------
    session : `requests.Session`
        Requests session that can take ``get`` and ``post`` methods, for
        example.

    Notes
    -----
    This function is based on
    https://www.peterbe.com/plog/best-practice-with-retries-with-requests
    by Peter Bengtsson.
    """
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session
