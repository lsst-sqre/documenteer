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

from sphinx.builders.linkcheck import (
    CheckExternalLinksBuilder,
    HyperlinkCollector,
)
from sphinx.util import logging

from ..conf._configsource import ConfigSource, detect_config_source
from ..storage.githuboidc import GitHubOidcTokenFetcher
from ..storage.linkcheckclient import (
    DEFAULT_BASE_URL,
    CheckedUrl,
    CheckRunStatus,
    CheckUrlStatus,
    ContributedResult,
    ContributionEnvironment,
    LinkCheck,
    LinkCheckClient,
    LinkCheckRequest,
    LinkCheckServiceError,
    LinkCheckSummary,
    LinkCheckUnauthorizedError,
    SubmittedUrl,
)
from ..storage.locallinkchecker import LocalCheckResult, LocalLinkChecker
from ..version import __version__

if TYPE_CHECKING:
    from collections.abc import Container, Iterable, Mapping

    from docutils import nodes
    from sphinx.application import Sphinx
    from sphinx.config import Config
    from sphinx.util.typing import ExtensionMetadata

__all__ = [
    "DEFAULT_BRANCH_FLAG_ENV_VAR",
    "JSON_ARTIFACT_NAME",
    "ReferencingPagesCollector",
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

_ORIGIN_BASE_URL_REMEDY = {
    ConfigSource.GUIDE: (
        "Set project.base_url or [sphinx.linkcheck] origin_base_url in "
        "documenteer.toml."
    ),
    # A technote's origin base URL is derived rather than authored:
    # get_technote_origin_base_url() prefers the canonical URL and falls
    # back to https://<id>.lsst.io, so it is empty only when both of
    # these technote.toml keys are missing.
    ConfigSource.TECHNOTE: (
        "Set [technote] canonical_url or [technote] id in technote.toml."
    ),
    ConfigSource.UNKNOWN: (
        "Set documenteer_linkcheck_origin_base_url in conf.py."
    ),
}
"""How to supply a missing origin base URL, per kind of project."""

_STRICT_SETTING = {
    ConfigSource.GUIDE: "[sphinx.linkcheck] strict = true in documenteer.toml",
    # Technotes get the conf.py form rather than a TOML key because
    # technote.toml's schema belongs to the technote package, not to
    # Documenteer.
    ConfigSource.TECHNOTE: "documenteer_linkcheck_strict = True in conf.py",
    ConfigSource.UNKNOWN: "documenteer_linkcheck_strict = True in conf.py",
}
"""How strict mode is spelled, per kind of project."""

_USE_SERVICE_SETTING = {
    ConfigSource.GUIDE: (
        "[sphinx.linkcheck] use_service = false in documenteer.toml"
    ),
    # Technotes get the conf.py form rather than a TOML key because
    # technote.toml's schema belongs to the technote package, not to
    # Documenteer.
    ConfigSource.TECHNOTE: (
        "documenteer_linkcheck_use_service = False in conf.py"
    ),
    ConfigSource.UNKNOWN: (
        "documenteer_linkcheck_use_service = False in conf.py"
    ),
}
"""How the link-check service is switched off in favor of Sphinx's
built-in builder, per kind of project."""

_BOT_BLOCK_STATUS_CODES = frozenset({403, 429})
"""HTTP status codes that read as bot protection rather than a broken
link.

Cloudflare's edge answers a blocked client with a 403 (and a 429 when it
is rate-limiting instead), which is exactly the signal that made Ook
report the URL ``blocked`` in the first place. A local recheck that lands
on one of these has confirmed the block, not a broken link.
"""

_PERMANENT_REDIRECT_STATUS_CODES = frozenset({301, 308})
"""Redirect status codes that make a working URL ``redirected`` rather
than plain ``ok``, matching Ook's definition of that status (a URL that
works via a *permanent* redirect)."""

_DEFAULT_LOCAL_RECHECK_TIMEOUT = 30.0
"""Per-request timeout for the local recheck, in seconds, used when the
project does not set ``linkcheck_timeout``."""


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


def _is_unverified(result: CheckedUrl) -> bool:
    """Whether the service's verdict for a URL rests on evidence nobody
    obtained, and so is worth rechecking from this build.

    Two verdicts qualify. ``blocked`` says the service's requests tripped
    a site's bot-protection edge, which it cannot tell apart from a site
    refusing everyone. ``broken`` with no status code says the service got
    no response at all — a TLS chain it could not build, a dropped
    connection, a name it could not resolve — which settles nothing about
    the link either, and which the build fails on regardless of ``strict``.

    A ``broken`` verdict carrying a status code is excluded on purpose:
    that is a definite answer the server itself gave, and a second opinion
    from the build has no standing to overturn it.

    Returns
    -------
    bool
        `True` if the URL should be rechecked locally.
    """
    if result.status is CheckUrlStatus.blocked:
        return True
    return (
        result.status is CheckUrlStatus.broken and result.status_code is None
    )


def _contributable_urls(check: LinkCheck) -> set[str]:
    """Select the URLs whose local observations the service will accept
    back.

    Ook applies a contributed result only to a URL its own stored state
    still has as ``blocked``, declining anything else with a
    ``not_blocked`` rejection. The recheck is wider than that — it also
    visits URLs the service reported ``broken`` without ever getting a
    response — so the observations it produces are not all eligible.

    Withholding the ineligible ones is the same courtesy the no-response
    filter in `_contribute_local_results` extends: do not send the service
    what it is going to refuse. Widening the service's eligibility is
    tracked separately; until then the build reads the current rule rather
    than filling the report with rejections.

    Returns
    -------
    set of str
        The URLs the service reported ``blocked``, taken from the check as
        the service returned it (before any local merge).
    """
    return {
        result.url
        for result in check.urls
        if result.status is CheckUrlStatus.blocked
    }


def _local_verdict(local: LocalCheckResult) -> CheckUrlStatus:
    """Translate a local observation into the status it warrants for a
    URL the service could not settle from its own vantage point.

    Only a failure the server itself answered with settles a URL as
    ``broken``. A failure that produced no response at all — a timeout, a
    connection reset, a DNS failure — settled nothing: bot protection does
    not always answer with a status code (an edge that dislikes a
    datacenter IP may simply drop the connection, and a GitHub Actions
    runner is a datacenter IP), and a transient network blip at the runner
    is not evidence about a link. This is the same standard `_is_unverified`
    applies to the *service's* observations, turned on the build's own: a
    verdict nobody obtained does not get to move a URL in either direction.

    Returns
    -------
    CheckUrlStatus
        ``ok`` (or ``redirected``, when the URL works only through a
        permanent redirect) when the build's own vantage point resolved
        the URL; ``blocked`` when the build was blocked too, or got no
        response at all, which `_merge_local_result` reads as "settled
        nothing" and leaves the service's verdict standing; ``broken``
        when the build got a definite HTTP failure the service could not
        see.
    """
    if local.is_ok:
        if local.redirect_status_code in _PERMANENT_REDIRECT_STATUS_CODES:
            return CheckUrlStatus.redirected
        return CheckUrlStatus.ok
    if (
        local.status_code is None
        or local.status_code in _BOT_BLOCK_STATUS_CODES
    ):
        return CheckUrlStatus.blocked
    return CheckUrlStatus.broken


def _merge_local_result(
    result: CheckedUrl, local: LocalCheckResult
) -> CheckedUrl:
    """Fold one local observation into the service's result for that URL.

    A local observation only overwrites the service's evidence when it
    changes the verdict. A URL the recheck settled nothing about — blocked
    from the build's vantage point too, or unanswered altogether — is left
    exactly as the service reported it, while a URL the build resolved or
    definitively failed is restated with the local evidence. See
    `_local_verdict` for which observations count as settling one.

    That conservatism cuts both ways, and deliberately so: a URL the
    service reported ``broken`` because it got no response, and which the
    build could not reach either, keeps its ``broken`` status and still
    fails the build. Two vantage points failing to reach a link is not
    proof the link works.
    """
    status = _local_verdict(local)
    if status is CheckUrlStatus.blocked:
        return result
    return result.model_copy(
        update={
            "status": status,
            "status_code": local.status_code,
            "redirect_status_code": local.redirect_status_code,
            "redirect_url": local.redirect_url,
            "error": local.error,
            "date_checked": local.date_checked,
        }
    )


def _merge_local_results(
    check: LinkCheck, local_results: Mapping[str, LocalCheckResult]
) -> LinkCheck:
    """Rebuild a completed check with local observations folded in.

    The summary is adjusted rather than recomputed: each URL whose verdict
    the recheck changed moves out of the count for whatever status the
    service gave it — ``blocked``, or the ``broken`` it could not reach —
    and into its new status's count, leaving the service's own counts for
    every other URL untouched.
    """
    counts = check.summary.model_dump()
    urls: list[CheckedUrl] = []
    for result in check.urls:
        local = local_results.get(result.url)
        if local is None:
            urls.append(result)
            continue
        merged = _merge_local_result(result, local)
        if merged.status is not result.status:
            counts[result.status.value] -= 1
            counts[merged.status.value] += 1
        urls.append(merged)
    return check.model_copy(
        update={
            "urls": urls,
            "summary": LinkCheckSummary.model_validate(counts),
        }
    )


class ReferencingPagesCollector(HyperlinkCollector):
    """Collect every docname that references each hyperlink URI.

    Sphinx's built-in `~sphinx.builders.linkcheck.HyperlinkCollector`
    keeps only the *first* occurrence's docname per URI (``if uri not in
    hyperlinks``), so a URL referenced from several pages is checked with
    only one referencing page. This post-transform runs alongside the
    built-in collector — same ``builders`` gate and ``default_priority``,
    and it reuses the built-in ``run`` and ``find_uri`` so the collected
    URI set matches the builder's ``hyperlinks`` exactly — but overrides
    ``_add_uri`` to accumulate the *complete* set of referencing docnames
    onto the builder's ``_referencing_pages`` mapping.
    """

    def _add_uri(self, uri: str, node: nodes.Element) -> None:
        # node is required by the overridden signature but unused here:
        # unlike the built-in we track referencing pages, not line
        # numbers.
        env = self.env
        # Reach the builder the way the version-appropriate built-in
        # collector does: env._app.builder (Sphinx 9), falling back to
        # env.app.builder (Sphinx 8). Avoids SphinxTransform.app, which is
        # deprecated in Sphinx 9.
        app = getattr(env, "_app", None) or env.app
        builder = app.builder
        if not isinstance(builder, ServiceLinkCheckBuilder):
            # The built-in linkcheck builder (documenteer_linkcheck_use_service
            # = false) has no _referencing_pages mapping and ignores it.
            return
        # Mirror the built-in's linkcheck-process-uri transform so our keys
        # match the builder's ``hyperlinks`` keys even when a handler
        # rewrites URIs.
        newuri = env.events.emit_firstresult("linkcheck-process-uri", uri)
        if newuri:
            uri = newuri
        # _referencing_pages is this collector's designated hand-off slot
        # on the service builder (peers in this module); the write goes
        # nowhere else.
        builder._referencing_pages.setdefault(uri, set()).add(  # noqa: SLF001
            self._current_docname()
        )

    def _current_docname(self) -> str:
        # BuildEnvironment.docname (Sphinx 8) became
        # current_document.docname (Sphinx 9); support both.
        current_document = getattr(self.env, "current_document", None)
        if current_document is not None:
            return current_document.docname
        return self.env.docname


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

    #: URI to the complete set of docnames that reference it, populated by
    #: `ReferencingPagesCollector` during the write phase.
    _referencing_pages: dict[str, set[str]]

    #: Which kind of Documenteer project is being built, used to word the
    #: build-log messages that name configuration settings.
    _config_source: ConfigSource

    def init(self) -> None:
        """Initialize the builder, adding the referencing-pages mapping the
        `ReferencingPagesCollector` post-transform populates and resolving
        the kind of project being built.

        The project kind is resolved once here, rather than once per
        message, from ``self.confdir`` (which `~sphinx.builders.Builder`
        sets from ``app.confdir``).
        """
        super().init()
        self._referencing_pages = {}
        self._config_source = detect_config_source(self.confdir)

    def finish(self) -> None:
        """Submit the collected hyperlinks to the link-check service and
        report the results.

        Whatever keeps the service from answering, link checking still
        happens: both handlers below end in `_fall_back_to_builtin`, which
        runs Sphinx's built-in in-process check. A missing or rejected
        ``OOK_TOKEN`` (`_handle_unauthorized_error`) falls back in every
        mode, because a token-less project simply isn't using the service.
        Other service problems — an unreachable service or an exhausted
        polling budget — go to `_handle_service_error`, which falls back
        by default and fails the build only in strict mode.
        """
        origin_base_url = self.config.documenteer_linkcheck_origin_base_url
        if not origin_base_url:
            logger.warning(
                "No origin base URL is available for the link-check "
                "service. %s",
                _ORIGIN_BASE_URL_REMEDY[self._config_source],
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
        except LinkCheckUnauthorizedError as e:
            # A missing or rejected OOK_TOKEN means this project isn't
            # using the service; fall back to the built-in check in any
            # mode (subclass must be caught before LinkCheckServiceError).
            self._handle_unauthorized_error(e)
            return
        except LinkCheckServiceError as e:
            self._handle_service_error(e)
            return
        local_results: dict[str, LocalCheckResult] = {}
        if self.config.documenteer_linkcheck_recheck_unverified:
            # Read off which URLs the service will accept a contribution
            # for before the recheck rewrites their statuses: eligibility
            # is decided by the *service's* stored state, not by what this
            # build went on to observe.
            contributable = _contributable_urls(check)
            check, local_results = self._recheck_unverified_urls(check)
            if local_results:
                self._contribute_local_results(
                    client,
                    check.id,
                    local_results.values(),
                    contributable=contributable,
                )
        self._report(check, locally_rechecked=set(local_results))

    def _recheck_unverified_urls(
        self, check: LinkCheck
    ) -> tuple[LinkCheck, dict[str, LocalCheckResult]]:
        """Recheck from this build's own vantage point the URLs the
        service could not settle from its own, and fold what it observes
        into the results.

        Two of the service's verdicts rest on evidence nobody actually
        obtained about the link itself. Ook reports a URL ``blocked``
        when its egress trips a site's bot protection, and it reports one
        ``broken`` with no status code at all when it got no response —
        a TLS chain it could not build, a connection the far end dropped,
        a name it could not resolve. A documentation build usually runs
        somewhere else entirely — a GitHub Actions runner the same site is
        happy to serve, with a different trust store and a different route
        — so the build can often settle what the service could not.

        A ``broken`` verdict that *does* carry a status code is a definite
        answer from the server, so it stays authoritative and is never
        rechecked. Only the unsettled URLs are visited, one at a time with
        a politeness delay, so this stays a handful of requests rather
        than a second link check.

        Returns
        -------
        tuple
            The check with the local observations merged in, and the local
            observations themselves, keyed by URL.
        """
        unverified = [
            result.url for result in check.urls if _is_unverified(result)
        ]
        if not unverified:
            return check, {}

        logger.info(
            "Rechecking unverified URLs from this build's own vantage point"
        )
        checker = LocalLinkChecker(
            timeout=self.config.linkcheck_timeout
            or _DEFAULT_LOCAL_RECHECK_TIMEOUT
        )
        local_results = {
            local.url: local for local in checker.check_urls(unverified)
        }
        merged = _merge_local_results(check, local_results)
        self._log_recheck_outcome(merged, set(unverified))
        return merged, local_results

    def _contribute_local_results(
        self,
        client: LinkCheckClient,
        check_id: str,
        local_results: Iterable[LocalCheckResult],
        *,
        contributable: Container[str],
    ) -> None:
        """Hand the build's own observations back to the link-check service.

        What this build learned about a URL Ook could only report as
        blocked is worth more than this one report: contributed back, it
        improves the service's stored state for every project that
        references the same URL. Successes and failures alike are sent —
        the service treats a contributed observation exactly as it treats
        one of its own checks.

        That reach is also why an observation that settled nothing is
        withheld. A URL that answered this build with nothing at all
        rewrites nothing locally (see `_local_verdict`), and contributing
        it would put a runner's network blip into the state every other
        project's build reads.

        ``contributable`` withholds the rest, for a different reason: the
        service accepts a result only for a URL it has stored as
        ``blocked``, so an observation for one it reported ``broken``
        would come back rejected (see `_contributable_urls`). Both filters
        can empty the batch, and an empty batch skips the token mint
        entirely rather than posting nothing.

        The contribution is attested by a GitHub Actions OIDC id token
        minted for the service's own base URL, so the service records the
        workflow run's verified claims as the provenance. That token only
        exists inside a workflow job holding the ``id-token: write``
        permission; anywhere else the contribution is simply skipped, and
        the recheck still informs this build's own report.

        Nothing here can fail the build. A contribution is an improvement
        to somebody else's future build, so every way it can go wrong —
        no token to attest with, a service that will not take the batch,
        an entry the service declines — is reported at info level and
        left at that. Info level rather than warning is load-bearing, not
        cosmetic: a warnings-as-errors (``-W``) build fails on any
        warning, so reporting a contribution problem as one would fail
        the very build the message says is unaffected.
        """
        results = [
            ContributedResult.model_validate(local, from_attributes=True)
            for local in local_results
            # An observation with no status code got no response at all,
            # which settles nothing about the URL — the same reason
            # `_merge_local_result` refuses to apply it to this build's
            # own report. An observation for a URL the service did not
            # store as ``blocked`` is one it will not apply at all.
            if local.status_code is not None and local.url in contributable
        ]
        if not results:
            logger.info(
                "Not contributing the local recheck's results to the "
                "link-check service: the recheck observed nothing worth "
                "contributing that the service would accept."
            )
            return
        token = GitHubOidcTokenFetcher().fetch_id_token(client.oidc_audience)
        if token.token is None:
            logger.info(
                "Not contributing the local recheck's results to the "
                "link-check service: %s",
                token.unavailable_reason,
            )
            return
        try:
            report = client.contribute_results(
                check_id,
                results,
                id_token=token.token,
                environment=ContributionEnvironment.from_github_actions(),
            )
        except LinkCheckServiceError as e:
            # Reported at info level, like every other unactionable
            # link-check outcome, so a warnings-as-errors (``-W``) build
            # does not fail on it. As a warning this message would
            # falsify its own last sentence: any undeliverable
            # contribution — a deployment not serving the endpoint yet, a
            # 502 that outlasts the retry ladder — would fail the build it
            # says is unaffected (mirrors the ``-W`` reasoning in
            # `_fall_back_to_builtin` and `_report`).
            logger.info(
                "Could not contribute the local recheck's results to the "
                "link-check service: %s The build is unaffected.",
                e,
            )
            return
        logger.info(
            "Contributed %d link-check result%s to %s (%d accepted, "
            "%d rejected)",
            len(results),
            "" if len(results) == 1 else "s",
            report.provenance.repository,
            len(report.accepted),
            len(report.rejected),
        )
        for rejection in report.rejected:
            # A rejection is the service declining one entry, not a
            # problem with the documentation being built, so it is
            # reported at info level like the other unactionable
            # link-check outcomes. The reason renders as its wire value
            # whether it is a known ContributionRejectionReason (a
            # StrEnum) or a plain string the service has since added.
            logger.info(
                "Contribution rejected for %s (%s): %s",
                rejection.url,
                rejection.reason,
                rejection.message,
            )

    @staticmethod
    def _log_recheck_outcome(merged: LinkCheck, rechecked: set[str]) -> None:
        """Report what the local recheck settled, in one line.

        The three counts are the three outcomes: the build resolved the
        URL, the build failed to settle it (so the service's verdict
        stands, whether that was ``blocked`` or a ``broken`` it could not
        reach), or the URL is failing. "Still unverified" rather than
        "still blocked" because the rechecked population is now mixed —
        not every URL on this path arrived bot-blocked.
        """
        statuses = [
            result.status for result in merged.urls if result.url in rechecked
        ]
        still_unverified = statuses.count(CheckUrlStatus.blocked)
        broken = statuses.count(CheckUrlStatus.broken)
        logger.info(
            "Local recheck: %d verified, %d still unverified, %d failing",
            len(statuses) - still_unverified - broken,
            still_unverified,
            broken,
        )

    def _fall_back_to_builtin(self) -> None:
        """Check this build's links with Sphinx's built-in in-process
        link checker instead of the service.

        This is the shared tail of every path that could not get results
        out of the service. Skipping link checking would be a silent
        regression for projects that already had a working ``linkcheck``
        pipeline before adopting the service, so the builder runs Sphinx's
        own `~sphinx.builders.linkcheck.CheckExternalLinksBuilder` check
        in-process via ``super().finish()``. That built-in check writes
        ``output.txt``/``output.json`` and sets the exit status on broken
        links, so its own result — not ``strict`` — decides whether the
        build fails on a fallback path.

        The price is time: the built-in check visits every external link
        from this machine, with none of the caching or retry buffering
        that made the service worth using. Paying it beats reporting
        nothing about the links, but it is why strict mode fails outright
        rather than falling back — a project that asked for service
        problems to be fatal has said it does not want the substitute.

        Each caller announces its own cause before calling this, and does
        so at info level rather than as a warning, so a warnings-as-errors
        (``-W``) build does not fail merely because the service was out of
        reach (mirrors the ``-W`` reasoning in `_report`).
        """
        super().finish()

    def _handle_unauthorized_error(
        self, error: LinkCheckUnauthorizedError
    ) -> None:
        """Fall back to Sphinx's built-in in-process link checker when the
        Ook API token is unavailable.

        A missing or rejected ``OOK_TOKEN`` means the project isn't using
        the link-check service, which is a configuration state rather than
        a service problem — so this falls back in every mode, ``strict``
        included, and never fails the build on its own. For the
        missing-token case the client's token guard raises before any
        request, so no wasted network call is made to the service.

        The message names whichever way of selecting the built-in builder
        explicitly the project being built actually has: a guide's
        ``[sphinx.linkcheck] use_service = false`` in ``documenteer.toml``,
        or a technote's ``documenteer_linkcheck_use_service = False`` in
        ``conf.py``.
        """
        logger.info(
            "Ook API token unavailable (%s); falling back to Sphinx's "
            "built-in in-process link checker so link checking still runs. "
            "Set OOK_TOKEN to use the Ook link-check service, or set %s to "
            "select the built-in builder explicitly.",
            error,
            _USE_SERVICE_SETTING[self._config_source],
        )
        self._fall_back_to_builtin()

    def _handle_service_error(self, error: LinkCheckServiceError) -> None:
        """Handle a genuine link-check service problem: an unreachable
        service or an exhausted polling budget.

        By default the build degrades to Sphinx's built-in in-process
        checker (`_fall_back_to_builtin`) rather than failing, so a
        transient service problem costs the build time but not its links:
        they are all still checked, and it is the built-in check's own
        result that decides the exit status. The announcement is info
        level, not a warning, because Rubin builds run with ``-W`` — a
        warning here would fail every build unlucky enough to coincide
        with an Ook outage.

        Strict mode instead makes these conditions fail the build outright,
        with no fallback: a project that set ``strict`` asked for service
        problems to be fatal, so substituting a slower local check would
        answer a question it did not ask. It is set with
        ``[sphinx.linkcheck] strict = true`` in a guide's
        ``documenteer.toml``, or ``documenteer_linkcheck_strict = True``
        in a technote's ``conf.py``; each message names whichever of the
        two the project being built actually uses. A missing or rejected
        ``OOK_TOKEN`` is handled separately by `_handle_unauthorized_error`,
        not here.

        The service error is appended last because it embeds the client's
        own message, which runs to several lines for a connection failure.
        Everything the reader can act on therefore stays on the first line
        of the report.
        """
        strict_setting = _STRICT_SETTING[self._config_source]
        if self.config.documenteer_linkcheck_strict:
            logger.warning(
                "Link check failed: %s The build fails because %s.",
                error,
                strict_setting,
            )
            self._set_failure_status()
        else:
            logger.info(
                "Link check service unavailable; falling back to Sphinx's "
                "built-in in-process link checker so link checking still "
                "runs. Checking every link in-process takes longer than the "
                "service does, and broken links it finds fail the build. "
                "Set %s to fail the build on the service problem itself "
                "instead. The service problem was: %s",
                strict_setting,
                error,
            )
            self._fall_back_to_builtin()

    def _referencing_page_sets(self) -> dict[str, set[str]]:
        """Map each collected hyperlink URI to the complete set of docnames
        that reference it.

        The `ReferencingPagesCollector` post-transform accumulates the full
        set of referencing pages per URI; the builder's ``hyperlinks`` (from
        the built-in collector) is the source of truth for *which* URIs were
        collected. Every collected URI gets an entry, falling back to the
        built-in first-occurrence docname if the collector recorded nothing
        for it.
        """
        return {
            uri: set(self._referencing_pages.get(uri) or {hyperlink.docname})
            for uri, hyperlink in self.hyperlinks.items()
        }

    def _collect_submission_urls(self) -> list[SubmittedUrl]:
        """Build the URL submission list from the collected hyperlinks.

        Each URL is submitted with every page that references it (sorted for
        a deterministic payload). URIs that Sphinx's built-in linkcheck
        builder never checks are filtered out (see `_is_checkable_uri`), and
        the ``linkcheck_ignore`` patterns are applied client-side, so neither
        non-checkable nor ignored URLs are ever submitted to the service.
        """
        ignore_patterns = [
            re.compile(pattern) for pattern in self.config.linkcheck_ignore
        ]
        urls: list[SubmittedUrl] = []
        for uri, docnames in self._referencing_page_sets().items():
            if not _is_checkable_uri(uri):
                continue
            if any(pattern.match(uri) for pattern in ignore_patterns):
                continue
            urls.append(SubmittedUrl(url=uri, origin_paths=sorted(docnames)))
        return urls

    def _report(
        self, check: LinkCheck, *, locally_rechecked: set[str]
    ) -> None:
        """Report the completed link check and set the exit status.

        Prints the summary counts by status and a detail line for every
        link that needs attention. ``broken`` links fail the build with a
        nonzero exit status and are reported as warnings; ``redirected``,
        ``failing``, ``unsupported``, and ``blocked`` links are reported at
        info level so a warnings-as-errors (``-W``) build does not fail on
        them. ``blocked`` links (bot protection) are unverifiable from CI's
        vantage point, not broken, so they never fail the build.

        ``locally_rechecked`` names the URLs the local recheck visited, so
        a URL the build could not settle either — still blocked, or still
        unreachable — can say that both vantage points looked rather than
        leaving the reader to guess.
        """
        artifact_path = self._write_json_artifact(
            check, locally_rechecked=locally_rechecked
        )

        logger.info("")
        logger.info("Link check complete: %s", check.self_url)
        if check.date_completed is not None:
            runtime = (
                check.date_completed - check.date_created
            ).total_seconds()
            logger.info("%11s: %.1f s", "runtime", runtime)
        for status in CheckUrlStatus:
            count = getattr(check.summary, status.value)
            logger.info("%11s: %d", status.value, count)

        for result in check.urls:
            if result.status in (CheckUrlStatus.ok, CheckUrlStatus.pending):
                continue
            message = self._describe_result(
                result, locally_rechecked=result.url in locally_rechecked
            )
            # Only ``broken`` links fail the build (via the statuscode set
            # below), so they are reported as warnings. ``redirected``,
            # ``failing``, ``unsupported``, and ``blocked`` links are
            # reported at info level so a warnings-as-errors (``-W``) build
            # does not fail on them. This mirrors Sphinx's built-in
            # linkcheck, which fails via a nonzero statuscode for broken
            # links and logs redirects at info level by default.
            if result.status is CheckUrlStatus.broken:
                logger.warning(message)
            else:
                logger.info(message)

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
        self, check: LinkCheck, *, locally_rechecked: set[str]
    ) -> Path:
        """Write the machine-readable results artifact to the build
        output directory.

        The artifact holds the full check from the service, with each
        per-URL result annotated with the pages the URL occurs on. Those
        pages come straight from the service's ``origin_paths``, surfaced
        under the artifact's stable ``pages`` key. Each result also
        carries a ``locally_rechecked`` flag, so a consumer can tell a
        verdict the build itself settled from one the service reached
        alone.
        """
        data = check.model_dump(mode="json")
        for url_data in data["urls"]:
            url_data["pages"] = url_data.pop("origin_paths")
            url_data["locally_rechecked"] = (
                url_data["url"] in locally_rechecked
            )
        artifact_path = Path(self.outdir) / JSON_ARTIFACT_NAME
        artifact_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8"
        )
        return artifact_path

    @staticmethod
    def _describe_result(
        result: CheckedUrl, *, locally_rechecked: bool = False
    ) -> str:
        """Format the detail report line for one checked URL.

        The pages the URL occurs on come from the service's per-URL
        ``origin_paths``. ``locally_rechecked`` marks a URL the build
        rechecked itself, which sharpens the bot-protection caveat from a
        single vantage point's guess into a confirmed block, and which a
        ``broken`` result nobody got a response for needs for a different
        reason: a reader has to be able to tell "the service could not
        reach it and neither could this build" — two vantage points, one
        answer — from "the service could not reach it and nobody looked
        again". Only the first is worth acting on as a broken link.
        """
        page_list = ", ".join(result.origin_paths) or "unknown"
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
        if result.status is CheckUrlStatus.blocked:
            # Ook reports ``blocked`` when a URL trips a site's bot
            # protection (typically a Cloudflare 403). That is
            # unverifiable from CI's vantage point rather than genuinely
            # broken, so the detail line says as much.
            caveat = "likely bot protection; unverifiable from CI"
            if locally_rechecked:
                caveat += " or from this build"
            parts.append(caveat)
        elif (
            result.status is CheckUrlStatus.broken
            and result.status_code is None
            and locally_rechecked
        ):
            # A ``broken`` result with no status code that survived the
            # recheck is the one broken link the build fails on without
            # anyone having gotten an answer from the server. Saying so
            # keeps the reader from chasing a URL that may well be fine
            # from their own machine.
            parts.append(
                "no response from the link-check service or from this build"
            )
        return " - ".join(parts)


def _apply_builder_override(app: Sphinx, config: Config) -> None:
    """Override Sphinx's built-in linkcheck builder with the
    service-backed builder, unless disabled.

    The override decision needs the resolved configuration, so it runs on
    ``config-inited`` (which Sphinx emits after extension setup but
    before the builder is instantiated). When
    ``documenteer_linkcheck_use_service`` is false the override is not
    applied and Sphinx's built-in ``linkcheck`` builder runs as-is — the
    escape hatch for projects that want in-process link checking. A guide
    turns it off with ``[sphinx.linkcheck] use_service = false`` in
    ``documenteer.toml``; a technote sets
    ``documenteer_linkcheck_use_service = False`` in its ``conf.py``.
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

    # Runs alongside the built-in HyperlinkCollector (both gated to the
    # "linkcheck" builder) to record every page each URL is referenced from.
    app.add_post_transform(ReferencingPagesCollector)

    app.add_config_value("documenteer_linkcheck_use_service", True, "")
    app.add_config_value(
        "documenteer_linkcheck_service_url", DEFAULT_BASE_URL, ""
    )
    app.add_config_value("documenteer_linkcheck_poll_budget", 300, "")
    app.add_config_value("documenteer_linkcheck_strict", False, "")
    app.add_config_value("documenteer_linkcheck_recheck_unverified", True, "")
    app.add_config_value("documenteer_linkcheck_origin_base_url", None, "")
    app.add_config_value(
        "documenteer_linkcheck_default_branch_name", "main", ""
    )

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
