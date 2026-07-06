"""Sphinx linkcheck builder backed by Ook's link-check service.

This extension registers a builder over Sphinx's built-in ``linkcheck``
name so existing ``make linkcheck`` invocations transparently submit the
project's external links to Ook's link-check service instead of checking
each link in-process. The service caches results and retries failing
links on a ladder, so documentation builds no longer fail on transient
third-party outages.
"""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

from sphinx.builders.linkcheck import CheckExternalLinksBuilder
from sphinx.util import logging

from ..storage.linkcheckclient import (
    DEFAULT_BASE_URL,
    CheckRunStatus,
    CheckUrlStatus,
    LinkCheck,
    LinkCheckClient,
    LinkCheckRequest,
    SubmittedUrl,
)
from ..version import __version__

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sphinx.application import Sphinx
    from sphinx.util.typing import ExtensionMetadata

__all__ = [
    "DEFAULT_BRANCH_FLAG_ENV_VAR",
    "ServiceLinkCheckBuilder",
    "resolve_default_branch_flag",
    "setup",
]

logger = logging.getLogger(__name__)

DEFAULT_BRANCH_FLAG_ENV_VAR = "DOCUMENTEER_LINKCHECK_DEFAULT_BRANCH"
"""Environment variable that overrides default-branch build detection.

Set to ``true`` or ``false`` to force the flag either way regardless of
the GitHub Actions environment.
"""


def resolve_default_branch_flag(
    env: Mapping[str, str], default_branch: str
) -> bool:
    """Determine whether this build is a default-branch build.

    Only default-branch submissions replace an LTD project's recorded URL
    occurrences in the link-check service; all submissions receive full
    results.

    Parameters
    ----------
    env
        The process environment (usually `os.environ`).
    default_branch
        Name of the project's default Git branch (e.g. ``main``).

    Returns
    -------
    bool
        `True` for a GitHub Actions push build of the default branch,
        `False` for any other build (pull requests, pushes to other
        branches, local builds). The ``DOCUMENTEER_LINKCHECK_DEFAULT_BRANCH``
        environment variable overrides the detection in either direction.
    """
    override = env.get(DEFAULT_BRANCH_FLAG_ENV_VAR)
    if override is not None:
        return override.strip().lower() in {"1", "true", "yes"}
    if env.get("GITHUB_ACTIONS") == "true":
        return (
            env.get("GITHUB_EVENT_NAME") == "push"
            and env.get("GITHUB_REF_NAME") == default_branch
        )
    return False


class ServiceLinkCheckBuilder(CheckExternalLinksBuilder):
    """A linkcheck builder that checks links with Ook's link-check service.

    The builder reuses `sphinx.builders.linkcheck.CheckExternalLinksBuilder`'s
    hyperlink collection from the resolved doctrees (the built-in
    ``HyperlinkCollector`` post-transform keys on the ``linkcheck`` builder
    name), then submits the collected URLs to the service and polls for
    results instead of checking each link in-process.
    """

    name = "linkcheck"
    epilog = ""

    def finish(self) -> None:
        """Submit the collected hyperlinks to the link-check service and
        report the results.
        """
        slug = self.config.documenteer_linkcheck_slug
        if not slug:
            logger.warning(
                "No LSST the Docs project slug is available for the "
                "link-check service. Set project.base_url or "
                "[sphinx.linkcheck] slug in documenteer.toml."
            )
            return

        urls = self._collect_submission_urls()
        if not urls:
            logger.info("No external links to check.")
            return

        request = LinkCheckRequest(
            ltd_slug=slug,
            default_branch=resolve_default_branch_flag(
                os.environ,
                self.config.documenteer_linkcheck_default_branch_name,
            ),
            urls=urls,
        )
        client = LinkCheckClient(
            base_url=self.config.documenteer_linkcheck_service_url
        )
        logger.info(
            "Submitting %d URLs to the link-check service for project %s",
            len(urls),
            slug,
        )
        check = client.submit_check(request)
        if check.status is not CheckRunStatus.complete:
            check = client.poll_check(
                check.id,
                budget=self.config.documenteer_linkcheck_poll_budget,
            )
        self._report(check)

    def _collect_submission_urls(self) -> list[SubmittedUrl]:
        """Build the URL submission list from the collected hyperlinks.

        The ``linkcheck_ignore`` patterns are applied client-side so
        ignored URLs are never submitted to the service.
        """
        ignore_patterns = [
            re.compile(pattern) for pattern in self.config.linkcheck_ignore
        ]
        urls: list[SubmittedUrl] = []
        for uri, hyperlink in self.hyperlinks.items():
            if any(pattern.match(uri) for pattern in ignore_patterns):
                continue
            urls.append(SubmittedUrl(url=uri, paths=[hyperlink.docname]))
        return urls

    def _report(self, check: LinkCheck) -> None:
        """Print a summary of the completed link check."""
        logger.info("")
        logger.info("Link check complete (Ook check id: %d)", check.id)
        for status in CheckUrlStatus:
            count = getattr(check.summary, status.value)
            logger.info("%11s: %d", status.value, count)


def setup(app: Sphinx) -> ExtensionMetadata:
    """Set up the linkcheckservice extension.

    Parameters
    ----------
    app
        The Sphinx application.

    Returns
    -------
    sphinx.util.typing.ExtensionMetadata
        Extension metadata for Sphinx.
    """
    # Override Sphinx's built-in linkcheck builder. The built-in
    # HyperlinkCollector post-transform and linkcheck_* config values are
    # registered by the sphinx.builders.linkcheck built-in extension and
    # continue to apply to this builder (the collector keys on the
    # "linkcheck" builder name).
    app.add_builder(ServiceLinkCheckBuilder, override=True)

    app.add_config_value("documenteer_linkcheck_use_service", True, "")
    app.add_config_value(
        "documenteer_linkcheck_service_url", DEFAULT_BASE_URL, ""
    )
    app.add_config_value("documenteer_linkcheck_poll_budget", 300, "")
    app.add_config_value("documenteer_linkcheck_strict", False, "")
    app.add_config_value("documenteer_linkcheck_slug", None, "")
    app.add_config_value(
        "documenteer_linkcheck_default_branch_name", "main", ""
    )

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
