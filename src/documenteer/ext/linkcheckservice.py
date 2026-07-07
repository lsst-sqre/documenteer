"""Sphinx linkcheck builder backed by Ook's link-check service.

This extension registers a builder over Sphinx's built-in ``linkcheck``
name so existing ``make linkcheck`` invocations transparently submit the
project's external links to Ook's link-check service instead of checking
each link in-process. The service caches results and retries failing
links on a ladder, so documentation builds no longer fail on transient
third-party outages.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

from sphinx.builders.linkcheck import CheckExternalLinksBuilder
from sphinx.util import logging

from ..storage.linkcheckclient import (
    DEFAULT_BASE_URL,
    CheckedUrl,
    CheckRunStatus,
    CheckUrlStatus,
    LinkCheck,
    LinkCheckClient,
    LinkCheckRequest,
    LinkCheckServiceError,
    SubmittedUrl,
)
from ..version import __version__

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sphinx.application import Sphinx
    from sphinx.config import Config
    from sphinx.util.typing import ExtensionMetadata

__all__ = [
    "DEFAULT_BRANCH_FLAG_ENV_VAR",
    "JSON_ARTIFACT_NAME",
    "ServiceLinkCheckBuilder",
    "resolve_default_branch_flag",
    "setup",
]

logger = logging.getLogger(__name__)

JSON_ARTIFACT_NAME = "linkcheck.json"
"""File name of the machine-readable results artifact, written to the
build output directory."""

DEFAULT_BRANCH_FLAG_ENV_VAR = "DOCUMENTEER_LINKCHECK_DEFAULT_BRANCH"
"""Environment variable that overrides default-branch build detection.

Set to ``true`` or ``false`` to force the flag either way regardless of
the GitHub Actions environment.
"""


def resolve_default_branch_flag(
    env: Mapping[str, str], default_branch: str
) -> bool:
    """Determine whether this build is a default-branch build.

    Default-branch builds are submitted to the link-check service as
    default-version builds of the origin website. Only default-version
    submissions replace the origin's recorded URL occurrences; all
    submissions receive full results.

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


def _is_checkable_uri(uri: str) -> bool:
    """Whether a collected hyperlink URI is one the link-check service
    should check.

    This mirrors the pre-network guard in Sphinx's built-in linkcheck
    builder (``HyperlinkAvailabilityCheckWorker._check`` in
    ``sphinx/builders/linkcheck.py``): the built-in never checks empty
    URIs, bare ``#fragment`` anchors, ``mailto:``/``tel:`` links, or
    non-``http(s)`` schemes. Sphinx's ``HyperlinkCollector`` collects a
    reference node's ``refuri`` verbatim (without requiring a ``://``
    scheme), so those URIs reach this builder; submitting them to Ook is
    wrong — fragment-only URIs in particular collapse to a spurious empty
    URL once Ook strips the fragment.

    Returns
    -------
    bool
        `True` if the URI is an ``http``/``https`` URL that should be
        submitted, `False` for the non-checkable URIs above.
    """
    if len(uri) == 0 or uri.startswith(("#", "mailto:", "tel:")):
        return False
    return uri.startswith(("http:", "https:"))


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
        origin_base_url = self.config.documenteer_linkcheck_origin_base_url
        if not origin_base_url:
            logger.warning(
                "No origin base URL is available for the link-check "
                "service. Set project.base_url or [sphinx.linkcheck] "
                "origin_base_url in documenteer.toml."
            )
            return

        urls = self._collect_submission_urls()
        if not urls:
            logger.info("No external links to check.")
            return

        request = LinkCheckRequest(
            origin_base_url=origin_base_url,
            is_default_version=resolve_default_branch_flag(
                os.environ,
                self.config.documenteer_linkcheck_default_branch_name,
            ),
            urls=urls,
        )
        client = LinkCheckClient(
            base_url=self.config.documenteer_linkcheck_service_url
        )
        logger.info(
            "Submitting %d URLs to the link-check service for %s",
            len(urls),
            origin_base_url,
        )
        # A 200 submission response means the check completed at
        # submission and its body already holds the full results; a 202
        # response's body is the pending check, polled at the Location
        # header (or its self_url) until complete.
        try:
            check, poll_url = client.submit_check(request)
            if check.status is not CheckRunStatus.complete:
                check = client.poll_check(
                    poll_url,
                    budget=self.config.documenteer_linkcheck_poll_budget,
                )
        except LinkCheckServiceError as e:
            self._handle_service_error(e)
            return
        self._report(check)

    def _handle_service_error(self, error: LinkCheckServiceError) -> None:
        """Handle a link-check service problem (unreachable service,
        missing/rejected token, or an exhausted polling budget).

        By default the build degrades gracefully: a warning is emitted
        and the build continues with a zero exit status, so documentation
        builds do not fail on a transient service problem. With
        ``[sphinx.linkcheck] strict = true`` in ``documenteer.toml`` the
        same conditions fail the build instead.
        """
        if self.config.documenteer_linkcheck_strict:
            logger.warning(
                "Link check failed: %s The build fails because "
                "[sphinx.linkcheck] strict = true in documenteer.toml.",
                error,
            )
            self._set_failure_status()
        else:
            logger.warning(
                "Link check skipped: %s The build continues; set "
                "[sphinx.linkcheck] strict = true in documenteer.toml to "
                "fail the build on link-check service problems instead.",
                error,
            )

    def _collect_submission_urls(self) -> list[SubmittedUrl]:
        """Build the URL submission list from the collected hyperlinks.

        URIs that Sphinx's built-in linkcheck builder never checks are
        filtered out (see `_is_checkable_uri`), and the ``linkcheck_ignore``
        patterns are applied client-side, so neither non-checkable nor
        ignored URLs are ever submitted to the service.
        """
        ignore_patterns = [
            re.compile(pattern) for pattern in self.config.linkcheck_ignore
        ]
        urls: list[SubmittedUrl] = []
        for uri, hyperlink in self.hyperlinks.items():
            if not _is_checkable_uri(uri):
                continue
            if any(pattern.match(uri) for pattern in ignore_patterns):
                continue
            urls.append(
                SubmittedUrl(url=uri, origin_paths=[hyperlink.docname])
            )
        return urls

    def _report(self, check: LinkCheck) -> None:
        """Report the completed link check and set the exit status.

        Prints the summary counts by status and a detail line for every
        link that needs attention. ``broken`` links fail the build with a
        nonzero exit status; ``redirected``, ``failing``, and
        ``unsupported`` links produce warnings only.
        """
        pages = {
            uri: [hyperlink.docname]
            for uri, hyperlink in self.hyperlinks.items()
        }
        artifact_path = self._write_json_artifact(check, pages)

        logger.info("")
        logger.info("Link check complete (Ook check id: %d)", check.id)
        for status in CheckUrlStatus:
            count = getattr(check.summary, status.value)
            logger.info("%11s: %d", status.value, count)

        for result in check.urls:
            if result.status in (CheckUrlStatus.ok, CheckUrlStatus.pending):
                continue
            logger.warning(self._describe_result(result, pages))

        logger.info("The full results are in %s", artifact_path)

        if check.summary.broken > 0:
            self._set_failure_status()

    def _set_failure_status(self) -> None:
        """Fail the build with a nonzero exit status."""
        # Builder.app was renamed to Builder._app in Sphinx 9 (the
        # public accessor is deprecated there but is all Sphinx 8 has).
        sphinx_app = getattr(self, "_app", None) or self.app
        sphinx_app.statuscode = 1

    def _write_json_artifact(
        self, check: LinkCheck, pages: Mapping[str, list[str]]
    ) -> Path:
        """Write the machine-readable results artifact to the build
        output directory.

        The artifact holds the full check from the service, with each
        per-URL result annotated with the pages the URL occurs on.
        """
        data = check.model_dump(mode="json")
        for url_data in data["urls"]:
            url_data["pages"] = pages.get(url_data["url"], [])
        artifact_path = Path(self.outdir) / JSON_ARTIFACT_NAME
        artifact_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8"
        )
        return artifact_path

    @staticmethod
    def _describe_result(
        result: CheckedUrl, pages: Mapping[str, list[str]]
    ) -> str:
        """Format the detail report line for one checked URL."""
        page_list = ", ".join(pages.get(result.url, [])) or "unknown"
        parts = [f"{result.status.value}: {result.url} (page: {page_list})"]
        if result.status_code is not None:
            parts.append(f"HTTP {result.status_code}")
        if result.redirect_url:
            redirect = f"redirects to {result.redirect_url}"
            if result.redirect_status_code is not None:
                redirect += f" (HTTP {result.redirect_status_code})"
            parts.append(redirect)
        if result.error:
            parts.append(result.error)
        return " - ".join(parts)


def _apply_builder_override(app: Sphinx, config: Config) -> None:
    """Override Sphinx's built-in linkcheck builder with the
    service-backed builder, unless disabled.

    The override decision needs the resolved configuration, so it runs on
    ``config-inited`` (which Sphinx emits after extension setup but
    before the builder is instantiated). With ``[sphinx.linkcheck]
    use_service = false`` in ``documenteer.toml`` the override is not
    applied and Sphinx's built-in ``linkcheck`` builder runs as-is — the
    escape hatch for projects that want in-process link checking.
    """
    if not config.documenteer_linkcheck_use_service:
        return
    # The built-in HyperlinkCollector post-transform and linkcheck_*
    # config values are registered by the sphinx.builders.linkcheck
    # built-in extension and continue to apply to this builder (the
    # collector keys on the "linkcheck" builder name).
    app.add_builder(ServiceLinkCheckBuilder, override=True)


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
    app.connect("config-inited", _apply_builder_override)

    app.add_config_value("documenteer_linkcheck_use_service", True, "")
    app.add_config_value(
        "documenteer_linkcheck_service_url", DEFAULT_BASE_URL, ""
    )
    app.add_config_value("documenteer_linkcheck_poll_budget", 300, "")
    app.add_config_value("documenteer_linkcheck_strict", False, "")
    app.add_config_value("documenteer_linkcheck_origin_base_url", None, "")
    app.add_config_value(
        "documenteer_linkcheck_default_branch_name", "main", ""
    )

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
