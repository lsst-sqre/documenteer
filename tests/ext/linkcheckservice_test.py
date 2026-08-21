"""Tests for the documenteer.ext.linkcheckservice extension."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pytest
import pytest_responses  # noqa: F401
from requests.exceptions import ConnectionError as RequestsConnectionError
from responses import RequestsMock
from sphinx.builders.linkcheck import CheckExternalLinksBuilder
from sphinx.testing.util import SphinxTestApp

from documenteer.ext.linkcheckservice import resolve_default_branch_flag
from documenteer.version import __version__

# Whether the guide preset's dependencies are importable; the test root
# builds the full user-guide stack (``from documenteer.conf.guide import *``).
_HAS_GUIDE_DEPS = importlib.util.find_spec("pydata_sphinx_theme") is not None

# Whether the technote preset's dependencies are importable; the technote
# test root builds the full technote stack
# (``from documenteer.conf.technote import *``).
_HAS_TECHNOTE_DEPS = importlib.util.find_spec("technote") is not None

OOK_BASE_URL = "https://roundtable.lsst.cloud/ook"

# An Ook Crockford base32 check id, treated as an opaque token by the
# client (never parsed as a number).
OOK_CHECK_ID = "a1b2-c3d4-e5f6-g7h8"

# Where a build contributes its local observations for that check.
CONTRIBUTIONS_URL = (
    f"{OOK_BASE_URL}/linkcheck/checks/{OOK_CHECK_ID}/contributions"
)

# The GitHub Actions id-token endpoint, registered with ``responses``
# without a query string so it matches whatever query the fetcher adds.
OIDC_TOKEN_ENDPOINT = "https://token.actions.githubusercontent.com/req"

# The external http(s) URLs the shared ``linkcheck-service`` test root
# references that Sphinx's built-in checker actually requests (the guide
# preset's linkcheck_ignore drops https://ls.st/, so it is never fetched).
TESTROOT_EXTERNAL_URLS = [
    "https://example.com/page",
    "https://www.lsst.io/",
    "https://example.org/resource",
]


@pytest.fixture(autouse=True)
def _outside_actions_oidc(monkeypatch: Any) -> None:
    """Keep every build in this module out of a workflow job that can mint
    an OIDC id token unless the test opts back in.

    These two variables exist in the ambient environment whenever the suite
    itself runs in a GitHub Actions job holding ``id-token: write``, which
    would silently turn every recheck test into a contributing one. Clearing
    them by default makes contribution something a test asks for.
    """
    monkeypatch.delenv("ACTIONS_ID_TOKEN_REQUEST_URL", raising=False)
    monkeypatch.delenv("ACTIONS_ID_TOKEN_REQUEST_TOKEN", raising=False)


def _warning_message(app: SphinxTestApp, needle: str) -> str:
    """Return the one warning message containing ``needle``.

    Sphinx writes each warning into the stream as ``WARNING: <message>``,
    and a message can span several lines — a service error embeds the
    underlying client error verbatim, and the test roots are not Git
    repositories, so every build also carries a multi-line
    sphinx-last-updated-by-git warning. Splitting the stream on those
    markers scopes an assertion to a single message, so a check that a
    message does *not* name some file cannot be defeated by a different
    warning in the same build.
    """
    blocks = [
        block
        for block in app.warning.getvalue().split("WARNING: ")
        if needle in block
    ]
    assert len(blocks) == 1, app.warning.getvalue()
    return blocks[0]


def _status_message(app: SphinxTestApp, needle: str) -> str:
    """Return the one status-stream line containing ``needle``.

    Info-level messages share the status stream with the build's ordinary
    progress output, so an assertion that a message does *not* name some
    file has to be scoped to that message rather than run over the whole
    stream. Each ``logger.info`` call writes one line, so the line
    carrying the needle is the whole message.
    """
    lines = [
        line for line in app.status.getvalue().splitlines() if needle in line
    ]
    assert len(lines) == 1, app.status.getvalue()
    return lines[0]


def _mock_builtin_head_ok(responses: RequestsMock, urls: list[str]) -> None:
    """Register 200 HEAD responses for the built-in linkcheck fallback.

    Sphinx's built-in ``CheckExternalLinksBuilder`` checks each external
    URL with a HEAD request (falling back to GET only if HEAD fails), so a
    200 HEAD response marks the link ``ok``. Registering exactly the URLs
    the built-in will request keeps ``assert_all_requests_are_fired`` happy.
    """
    for url in urls:
        responses.head(url, status=200)


def _checked_url(url: str, status: str = "ok", **overrides: Any) -> dict:
    """Create a per-URL result for a mocked Ook link-check response.

    ``origin_paths`` — the referencing pages Ook echoes back for the URL —
    defaults to ``["index"]`` (the single-page test roots' only docname);
    pass it as an override for multi-page roots.
    """
    result: dict[str, Any] = {
        "url": url,
        "status": status,
        "status_code": 200 if status == "ok" else None,
        "redirect_status_code": None,
        "redirect_url": None,
        "error": None,
        "checked_at": "2026-07-06T12:00:00Z",
        "origin_paths": ["index"],
    }
    result.update(overrides)
    return result


def _check_response(
    urls: list[dict], *, check_id: str = OOK_CHECK_ID, status: str = "complete"
) -> dict:
    """Create a link-check payload for a mocked Ook API."""
    summary: dict[str, int] = {}
    for url in urls:
        summary[url["status"]] = summary.get(url["status"], 0) + 1
    return {
        "id": check_id,
        "self_url": f"{OOK_BASE_URL}/linkcheck/checks/{check_id}",
        "origin_base_url": "https://example.lsst.io",
        "is_default_version": False,
        "status": status,
        "date_created": "2026-07-06T12:00:00Z",
        "date_completed": (
            "2026-07-06T12:00:05Z" if status == "complete" else None
        ),
        "summary": summary,
        "urls": urls,
    }


def _mock_submit_check(
    responses: RequestsMock, urls: list[dict], *, check_id: str = OOK_CHECK_ID
) -> None:
    """Register mocked responses for the async submit-then-poll flow: a
    202 whose body is the pending check and whose Location header is the
    poll URL, followed by the completed check at that location.
    """
    check_url = f"{OOK_BASE_URL}/linkcheck/checks/{check_id}"
    pending_urls = [
        {
            **url,
            "status": "pending",
            "status_code": None,
            "checked_at": None,
        }
        for url in urls
    ]
    responses.post(
        f"{OOK_BASE_URL}/linkcheck/checks",
        json=_check_response(
            pending_urls, check_id=check_id, status="pending"
        ),
        status=202,
        headers={"Location": check_url},
    )
    responses.get(
        check_url,
        json=_check_response(urls, check_id=check_id),
        status=200,
    )


def _mock_local_recheck(
    responses: RequestsMock, url: str, *, status: int
) -> None:
    """Register the local recheck's requests for one URL.

    The local checker mirrors Sphinx's HEAD-then-GET retrieval ladder, so
    a failing status is requested twice — once per rung — while a
    successful HEAD ends the ladder. Registering exactly what will be
    requested keeps ``assert_all_requests_are_fired`` happy.
    """
    responses.head(url, status=status)
    if status >= 400:
        responses.get(url, status=status)


def _mock_local_recheck_unanswered(
    responses: RequestsMock, url: str, *, error: str = "Connection reset"
) -> None:
    """Register a local recheck for one URL that gets no response at all.

    Both rungs of the retrieval ladder are registered, because a HEAD that
    never completes always falls through to the GET.
    """
    responses.head(url, body=RequestsConnectionError(error))
    responses.get(url, body=RequestsConnectionError(error))


def _set_actions_oidc_env(monkeypatch: Any) -> None:
    """Put the build in a GitHub Actions job that can mint an id token.

    These are the variables GitHub exports to a workflow job that requests
    the ``id-token: write`` permission, plus the run identity the advisory
    environment block is composed from.
    """
    monkeypatch.setenv(
        "ACTIONS_ID_TOKEN_REQUEST_URL",
        f"{OIDC_TOKEN_ENDPOINT}?api-version=2.0",
    )
    monkeypatch.setenv("ACTIONS_ID_TOKEN_REQUEST_TOKEN", "request-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "lsst-sqre/documenteer")
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")
    monkeypatch.setenv("GITHUB_RUN_ID", "42")


def _mock_oidc_token(responses: RequestsMock, token: str = "a.b.c") -> None:
    """Register the Actions id-token endpoint's response."""
    responses.get(OIDC_TOKEN_ENDPOINT, json={"value": token}, status=200)


def _contribution_report(
    *,
    accepted: list[dict[str, Any]] | None = None,
    rejected: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a contribution report payload matching the Ook API.

    The provenance block is the service's own record of the verified id
    token's claims, so it is fixed here rather than derived from what the
    client sent.
    """
    return {
        "check_id": OOK_CHECK_ID,
        "provenance": {
            "provider": "github_actions",
            "repository": "lsst-sqre/documenteer",
            "run_id": "42",
            "workflow_ref": (
                "lsst-sqre/documenteer/.github/workflows/ci.yaml@refs/heads/main"
            ),
            "run_url": (
                "https://github.com/lsst-sqre/documenteer/actions/runs/42"
            ),
            "checker_version": f"documenteer {__version__}",
        },
        "accepted": accepted if accepted is not None else [],
        "rejected": rejected if rejected is not None else [],
    }


def _mock_submit_check_completed(
    responses: RequestsMock, urls: list[dict], *, check_id: str = OOK_CHECK_ID
) -> None:
    """Register a mocked 200 submission response: the check completed at
    submission and its body already carries the full results.
    """
    check_url = f"{OOK_BASE_URL}/linkcheck/checks/{check_id}"
    responses.post(
        f"{OOK_BASE_URL}/linkcheck/checks",
        json=_check_response(urls, check_id=check_id),
        status=200,
        headers={"Location": check_url},
    )


def test_default_branch_flag_push_to_default() -> None:
    """A GitHub Actions push to the default branch is a default-branch
    build.
    """
    env = {
        "GITHUB_ACTIONS": "true",
        "GITHUB_EVENT_NAME": "push",
        "GITHUB_REF_NAME": "main",
    }
    assert resolve_default_branch_flag(env, "main") is True


def test_default_branch_flag_push_to_other_branch() -> None:
    """A GitHub Actions push to another branch is not a default-branch
    build.
    """
    env = {
        "GITHUB_ACTIONS": "true",
        "GITHUB_EVENT_NAME": "push",
        "GITHUB_REF_NAME": "tickets/DM-55386",
    }
    assert resolve_default_branch_flag(env, "main") is False


def test_default_branch_flag_pull_request() -> None:
    """A GitHub Actions pull request build is not a default-branch build."""
    env = {
        "GITHUB_ACTIONS": "true",
        "GITHUB_EVENT_NAME": "pull_request",
        "GITHUB_REF_NAME": "42/merge",
    }
    assert resolve_default_branch_flag(env, "main") is False


def test_default_branch_flag_env_override() -> None:
    """DOCUMENTEER_LINKCHECK_DEFAULT_BRANCH overrides the GitHub Actions
    detection in both directions.
    """
    pr_env = {
        "DOCUMENTEER_LINKCHECK_DEFAULT_BRANCH": "true",
        "GITHUB_ACTIONS": "true",
        "GITHUB_EVENT_NAME": "pull_request",
        "GITHUB_REF_NAME": "42/merge",
    }
    assert resolve_default_branch_flag(pr_env, "main") is True

    push_env = {
        "DOCUMENTEER_LINKCHECK_DEFAULT_BRANCH": "false",
        "GITHUB_ACTIONS": "true",
        "GITHUB_EVENT_NAME": "push",
        "GITHUB_REF_NAME": "main",
    }
    assert resolve_default_branch_flag(push_env, "main") is False


def test_default_branch_flag_outside_ci() -> None:
    """Outside GitHub Actions, builds are not default-branch builds."""
    assert resolve_default_branch_flag({}, "main") is False


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck", testroot="linkcheck-service", srcdir="linkcheck-service"
)
def test_guide_linkcheck_happy_path(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """A guide project built with the linkcheck builder against a mocked
    Ook API that reports all links ok exits 0 and prints a summary.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    # A GitHub Actions push build of the default branch.
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    monkeypatch.setenv("GITHUB_REF_NAME", "main")

    checked_urls = [
        _checked_url(url)
        for url in (
            "https://example.com/page",
            "https://www.lsst.io/",
            "https://example.org/resource",
        )
    ]
    _mock_submit_check(responses, checked_urls)

    app.build()

    # The happy path exits 0.
    assert app.statuscode == 0

    # A submission and a poll were made, with bearer auth from OOK_TOKEN.
    # The 202 response's Location header is the poll URL.
    assert len(responses.calls) == 2
    api_request = responses.calls[0].request
    assert api_request.headers["Authorization"] == "Bearer test-token"
    poll_request = responses.calls[1].request
    assert (
        poll_request.url == f"{OOK_BASE_URL}/linkcheck/checks/{OOK_CHECK_ID}"
    )

    # The submission payload carries the origin base URL derived from
    # project.base_url, the default-version flag from the GitHub Actions
    # env, and the URL + page-path list.
    assert api_request.body is not None
    payload = json.loads(api_request.body)
    assert payload["origin_base_url"] == "https://example.lsst.io"
    assert payload["is_default_version"] is True
    submitted = {url["url"]: url["origin_paths"] for url in payload["urls"]}
    assert submitted == {
        "https://example.com/page": ["index"],
        "https://www.lsst.io/": ["index"],
        "https://example.org/resource": ["index"],
    }

    # linkcheck_ignore patterns (the guide preset ignores https://ls.st/)
    # are applied client-side: ignored URLs are never submitted.
    assert not any(url.startswith("https://ls.st/") for url in submitted)

    # A summary is printed.
    status_output = app.status.getvalue()
    assert (
        f"Link check complete: {OOK_BASE_URL}/linkcheck/checks/{OOK_CHECK_ID}"
        in status_output
    )
    # The check runtime is reported in seconds (fixture: 12:00:00 -> 12:00:05).
    assert "runtime: 5.0 s" in status_output
    assert "ok: 3" in status_output


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service-filter",
    srcdir="linkcheck-service-filter",
)
def test_non_checkable_uris_filtered(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """URIs the built-in linkcheck builder never checks are filtered out
    client-side, so they are never submitted to the service.

    Sphinx's HyperlinkCollector collects a reference node's ``refuri``
    verbatim, including bare ``#fragment`` anchors, ``mailto:``/``tel:``
    links, and non-http(s) schemes. Without this filter those URIs get
    submitted (and Ook collapses fragment-only URIs to a spurious empty
    URL). Real http(s) URLs — minus ``linkcheck_ignore`` matches — are
    still submitted.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")

    checked_urls = [
        _checked_url(url)
        for url in (
            "https://example.com/page",
            "https://www.lsst.io/",
        )
    ]
    _mock_submit_check(responses, checked_urls)

    app.build()

    assert app.statuscode == 0

    api_request = responses.calls[0].request
    assert api_request.body is not None
    payload = json.loads(api_request.body)
    submitted = {url["url"] for url in payload["urls"]}

    # Only real http(s) URLs are submitted.
    assert submitted == {
        "https://example.com/page",
        "https://www.lsst.io/",
    }

    # Non-checkable URIs never appear in the submission payload: empty or
    # fragment-only anchors, mailto:, tel:, and non-http(s) schemes.
    assert not any(uri == "" or uri.startswith("#") for uri in submitted)
    assert not any(uri.startswith("mailto:") for uri in submitted)
    assert not any(uri.startswith("tel:") for uri in submitted)
    assert not any(uri.startswith("ftp:") for uri in submitted)

    # linkcheck_ignore filtering still applies alongside the new filter
    # (the guide preset ignores https://ls.st/).
    assert not any(uri.startswith("https://ls.st/") for uri in submitted)


@pytest.mark.skipif(
    not _HAS_TECHNOTE_DEPS, reason="technote dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="technote-linkcheck-service",
    srcdir="technote-linkcheck-service",
)
def test_technote_linkcheck_happy_path(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """A technote project built with the linkcheck builder against a
    mocked Ook API submits with the origin base URL derived from the
    technote's canonical URL and reports results end-to-end.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    # A GitHub Actions push build of the technote's default branch
    # (github_default_branch = "master" in the fixture's technote.toml).
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    monkeypatch.setenv("GITHUB_REF_NAME", "master")

    checked_urls = [
        _checked_url(url)
        for url in (
            "https://example.com/page",
            "https://www.lsst.io/",
        )
    ]
    _mock_submit_check(responses, checked_urls)

    app.build()

    # The happy path exits 0.
    assert app.statuscode == 0

    # A submission and a poll were made, with bearer auth from OOK_TOKEN.
    assert len(responses.calls) == 2
    api_request = responses.calls[0].request
    assert api_request.headers["Authorization"] == "Bearer test-token"

    # The submission payload carries the origin base URL derived from
    # the technote's canonical URL (normalized: lowercased host,
    # trailing slash stripped), the default-version flag matched against
    # technote.toml's github_default_branch, and the URL + page-path
    # list.
    assert api_request.body is not None
    payload = json.loads(api_request.body)
    assert payload["origin_base_url"] == "https://sqr-000.lsst.io"
    assert payload["is_default_version"] is True
    submitted = {url["url"]: url["origin_paths"] for url in payload["urls"]}
    assert submitted == {
        "https://example.com/page": ["index"],
        "https://www.lsst.io/": ["index"],
    }

    # linkcheck_ignore patterns (the fixture's technote.toml ignores
    # https://ls.st/) are applied client-side: ignored URLs are never
    # submitted.
    assert not any(url.startswith("https://ls.st/") for url in submitted)

    # A summary is printed.
    status_output = app.status.getvalue()
    assert (
        f"Link check complete: {OOK_BASE_URL}/linkcheck/checks/{OOK_CHECK_ID}"
        in status_output
    )
    assert "ok: 2" in status_output


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-no-origin",
    confoverrides={"documenteer_linkcheck_origin_base_url": None},
)
def test_guide_missing_origin_names_documenteer_toml(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """A guide with no origin base URL still gets the message naming the
    keys of its own configuration file.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")

    app.build()

    assert app.statuscode == 0
    assert not responses.calls

    message = _warning_message(app, "No origin base URL is available")
    assert "documenteer.toml" in message
    assert "project.base_url" in message
    assert "[sphinx.linkcheck] origin_base_url" in message


@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service-bare",
    srcdir="linkcheck-service-bare-no-origin",
)
def test_bare_missing_origin_names_sphinx_config_value(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """A project configured from ``conf.py`` alone — with neither TOML
    file beside it — is pointed at the Sphinx config value, naming no
    file it does not have.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")

    app.build()

    assert app.statuscode == 0
    assert not responses.calls

    message = _warning_message(app, "No origin base URL is available")
    assert "documenteer_linkcheck_origin_base_url" in message
    assert "conf.py" in message
    assert "documenteer.toml" not in message
    assert "technote.toml" not in message


@pytest.mark.skipif(
    not _HAS_TECHNOTE_DEPS, reason="technote dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="technote-linkcheck-service",
    srcdir="technote-linkcheck-service-no-origin",
    confoverrides={"documenteer_linkcheck_origin_base_url": None},
)
def test_technote_missing_origin_names_technote_toml(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """A technote with no derivable origin base URL is told to set keys
    that exist in its own configuration file, not a ``documenteer.toml``
    it does not have.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")

    app.build()

    # The missing-origin path returns before any submission.
    assert app.statuscode == 0
    assert not responses.calls

    message = _warning_message(app, "No origin base URL is available")
    assert "technote.toml" in message
    assert "[technote] canonical_url" in message
    assert "[technote] id" in message
    # A technote has no documenteer.toml, so the message must never name
    # one — nor the guide-only keys that live in it.
    assert "documenteer.toml" not in message
    assert "project.base_url" not in message


@pytest.mark.skipif(
    not _HAS_TECHNOTE_DEPS, reason="technote dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="technote-linkcheck-service",
    srcdir="technote-linkcheck-service-escape-hatch",
    confoverrides={"documenteer_linkcheck_use_service": False},
)
def test_technote_use_service_override(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """A technote can restore Sphinx's built-in linkcheck builder by
    overriding documenteer_linkcheck_use_service in its conf.py: the
    service builder override is not applied and the Ook service is never
    contacted.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")

    # The override fell through to the stock builder, not the
    # service-backed subclass.
    assert type(app.builder) is CheckExternalLinksBuilder

    # The responses mock intercepts the in-process link checks, so no
    # real network access happens during the build.
    app.build()

    # The Ook service was never contacted.
    assert not any(
        (call.request.url or "").startswith(OOK_BASE_URL)
        for call in responses.calls
    )

    # The stock builder wrote its own report, not the service artifact.
    assert (Path(app.outdir) / "output.txt").is_file()
    assert not (Path(app.outdir) / "linkcheck.json").exists()


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-immediate",
)
def test_submission_completed_at_200(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """A 200 submission response means the check completed at submission:
    the results are reported straight from the POST body with no polling
    round-trip.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    checked_urls = [
        _checked_url(url)
        for url in (
            "https://example.com/page",
            "https://www.lsst.io/",
            "https://example.org/resource",
        )
    ]
    _mock_submit_check_completed(responses, checked_urls)

    app.build()

    assert app.statuscode == 0

    # Only the POST was made: no polling round-trip.
    assert len(responses.calls) == 1

    # The results from the POST body are reported.
    status_output = app.status.getvalue()
    assert (
        f"Link check complete: {OOK_BASE_URL}/linkcheck/checks/{OOK_CHECK_ID}"
        in status_output
    )
    assert "ok: 3" in status_output


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-broken",
)
def test_broken_link_fails_build(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """A broken link reported by the Ook API causes a nonzero exit, and
    the summary lists it with its page and HTTP status.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    _mock_submit_check(
        responses,
        [
            _checked_url(
                "https://example.com/page",
                status="broken",
                status_code=404,
                error="404 Not Found",
            ),
            _checked_url("https://www.lsst.io/"),
        ],
    )

    app.build()

    assert app.statuscode == 1

    # The status counts include the broken link.
    status_output = app.status.getvalue()
    assert "broken: 1" in status_output
    assert "ok: 1" in status_output

    # The broken link is listed with its page and HTTP status.
    warning_output = app.warning.getvalue()
    assert "broken: https://example.com/page (page: index)" in warning_output
    assert "HTTP 404" in warning_output
    assert "404 Not Found" in warning_output


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-warnings",
)
def test_non_broken_statuses_pass_build(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """Redirected, failing, and unsupported links are reported at info
    level (not warnings) and the build exits 0; the detail lines appear
    in the summary output, not the warning stream.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    _mock_submit_check(
        responses,
        [
            _checked_url(
                "https://example.com/page",
                status="redirected",
                status_code=200,
                redirect_status_code=301,
                redirect_url="https://example.com/new-page",
            ),
            _checked_url(
                "https://www.lsst.io/",
                status="failing",
                status_code=503,
                error="503 Service Unavailable",
            ),
            _checked_url(
                "https://example.org/resource",
                status="unsupported",
                checked_at=None,
            ),
        ],
    )

    app.build()

    # Non-broken statuses do not fail the build.
    assert app.statuscode == 0

    # The status counts cover each non-broken status.
    status_output = app.status.getvalue()
    assert "redirected: 1" in status_output
    assert "failing: 1" in status_output
    assert "unsupported: 1" in status_output

    # Each link needing attention is reported at info level (in the status
    # stream), with its page, HTTP status, and redirect location where
    # applicable.
    assert (
        "redirected: https://example.com/page (page: index)" in status_output
    )
    assert "redirects to https://example.com/new-page (HTTP 301)" in (
        status_output
    )
    assert "failing: https://www.lsst.io/ (page: index)" in status_output
    assert "HTTP 503" in status_output
    assert "503 Service Unavailable" in status_output
    assert "unsupported: https://example.org/resource (page: index)" in (
        status_output
    )

    # None of the non-broken detail lines are emitted as warnings, so a
    # warnings-as-errors (-W) build would not fail on them.
    warning_output = app.warning.getvalue()
    assert "redirected:" not in warning_output
    assert "failing:" not in warning_output
    assert "unsupported:" not in warning_output


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-warningiserror",
    warningiserror=True,
    # The test root is not a Git repository, so sphinx-last-updated-by-git
    # warns; suppress it to isolate link-check reporting under -W.
    confoverrides={"suppress_warnings": ["git"]},
)
def test_non_broken_statuses_pass_warningiserror(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """With warnings-as-errors (Sphinx's ``-W``), a check that reports
    only redirected and unsupported links (no broken) still exits 0,
    because those statuses are reported at info level rather than as
    warnings.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    _mock_submit_check(
        responses,
        [
            _checked_url(
                "https://example.com/page",
                status="redirected",
                status_code=200,
                redirect_status_code=301,
                redirect_url="https://example.com/new-page",
            ),
            _checked_url("https://www.lsst.io/"),
            _checked_url(
                "https://example.org/resource",
                status="unsupported",
                checked_at=None,
            ),
        ],
    )

    # Under warningiserror, any logger.warning would raise SphinxWarning;
    # info-level reporting keeps the build green.
    app.build()

    assert app.statuscode == 0
    status_output = app.status.getvalue()
    assert "redirected: 1" in status_output
    assert "unsupported: 1" in status_output


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-blocked",
    confoverrides={"documenteer_linkcheck_recheck_blocked": False},
)
def test_blocked_links_reported_as_caveat(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """With the local recheck disabled, a bot-blocked link (Ook's
    ``blocked`` disposition) is a caveat, not a failure: it is reported at
    info level, labeled as likely bot protection, counted in the summary,
    and never fails the build.

    This is the report exactly as it read before the local recheck
    existed, so it doubles as the check that
    ``recheck_blocked = false`` leaves the old behavior intact.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    _mock_submit_check(
        responses,
        [
            _checked_url(
                "https://example.com/page",
                status="blocked",
                status_code=403,
                error="403 Forbidden",
            ),
            _checked_url("https://www.lsst.io/"),
        ],
    )

    app.build()

    # Blocked links are unverifiable from CI, not broken: the build exits 0.
    assert app.statuscode == 0

    # No local recheck was attempted: the only traffic is Ook's submit and
    # poll.
    assert [call.request.url for call in responses.calls] == [
        f"{OOK_BASE_URL}/linkcheck/checks",
        f"{OOK_BASE_URL}/linkcheck/checks/{OOK_CHECK_ID}",
    ]

    status_output = app.status.getvalue()
    # The summary counts the blocked link alongside the other statuses.
    assert "blocked: 1" in status_output
    assert "ok: 1" in status_output

    # The blocked link is reported at info level with its page, HTTP
    # status, error detail, and a bot-protection label.
    assert "blocked: https://example.com/page (page: index)" in status_output
    assert "HTTP 403" in status_output
    assert "403 Forbidden" in status_output
    assert "likely bot protection" in status_output

    # The blocked detail line is not a warning, so a warnings-as-errors
    # (-W) build would not fail on it.
    assert "blocked:" not in app.warning.getvalue()


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-recheck-verified",
)
def test_local_recheck_verifies_blocked_url(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """A URL Ook reports as bot-blocked but that resolves from the build's
    own vantage point is reported verified-OK, and its bot-block caveat
    clears.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    _mock_submit_check(
        responses,
        [
            _checked_url(
                "https://example.com/page",
                status="blocked",
                status_code=403,
                error="403 Forbidden",
            ),
            _checked_url("https://www.lsst.io/"),
        ],
    )
    _mock_local_recheck(responses, "https://example.com/page", status=200)

    app.build()

    assert app.statuscode == 0

    status_output = app.status.getvalue()
    # The local observation replaces Ook's: the URL now counts as ok.
    assert "blocked: 0" in status_output
    assert "ok: 2" in status_output

    # An ok URL has no detail line at all, so the caveat is gone.
    assert "likely bot protection" not in status_output
    assert "https://example.com/page (page: index)" not in status_output


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-recheck-redirected",
)
def test_local_recheck_reports_permanent_redirect(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """A bot-blocked URL the build resolves only through a *permanent*
    redirect is reported ``redirected``, not plain ok: the caveat clears
    but the stale link still asks to be fixed.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    _mock_submit_check(
        responses,
        [
            _checked_url(
                "https://example.com/page",
                status="blocked",
                status_code=403,
                error="403 Forbidden",
            ),
            _checked_url("https://www.lsst.io/"),
        ],
    )
    responses.head(
        "https://example.com/page",
        status=301,
        headers={"Location": "https://example.com/moved"},
    )
    responses.head("https://example.com/moved", status=200)

    app.build()

    assert app.statuscode == 0

    status_output = app.status.getvalue()
    assert "blocked: 0" in status_output
    assert "redirected: 1" in status_output
    assert (
        "redirected: https://example.com/page (page: index) - HTTP 200 - "
        "redirects to https://example.com/moved (HTTP 301)" in status_output
    )
    assert "likely bot protection" not in status_output


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-recheck-blocked",
)
def test_local_recheck_keeps_caveat_when_still_blocked(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """A URL that is bot-blocked from the build's vantage point too keeps
    its caveat, its ``blocked`` status, and the service's own evidence:
    the recheck settled nothing, so nothing is restated.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    _mock_submit_check(
        responses,
        [
            _checked_url(
                "https://example.com/page",
                status="blocked",
                status_code=403,
                error="403 Forbidden",
            ),
            _checked_url("https://www.lsst.io/"),
        ],
    )
    _mock_local_recheck(responses, "https://example.com/page", status=403)

    app.build()

    assert app.statuscode == 0

    status_output = app.status.getvalue()
    assert "blocked: 1" in status_output
    assert "403 Forbidden" in status_output
    # The caveat now records that the build's own vantage point was
    # blocked as well.
    assert (
        "likely bot protection; unverifiable from CI or from this build"
        in status_output
    )
    assert "blocked:" not in app.warning.getvalue()


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-recheck-unanswered",
)
def test_local_recheck_keeps_caveat_when_unanswered(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """A bot-blocked URL that answers the build with nothing at all — a
    connection reset, a timeout, a DNS failure — keeps its ``blocked``
    status and never fails the build.

    Bot protection does not always answer with a status code: an edge that
    dislikes a datacenter IP (which every GitHub Actions runner has) may
    just drop the connection. Promoting that to ``broken`` would turn a
    transient network blip at the runner into a build failure on evidence
    the build never obtained.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    _mock_submit_check(
        responses,
        [
            _checked_url(
                "https://example.com/page",
                status="blocked",
                status_code=403,
                error="403 Forbidden",
            ),
            _checked_url("https://www.lsst.io/"),
        ],
    )
    _mock_local_recheck_unanswered(responses, "https://example.com/page")

    app.build()

    # An inconclusive recheck costs the build nothing.
    assert app.statuscode == 0

    status_output = app.status.getvalue()
    assert "Local recheck: 0 verified, 1 still blocked, 0 failing" in (
        status_output
    )
    assert "blocked: 1" in status_output
    assert "broken: 0" in status_output
    # Nothing was learned, so the service's own evidence still stands.
    assert "403 Forbidden" in status_output
    assert "Connection reset" not in status_output
    assert "blocked:" not in app.warning.getvalue()


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-recheck-broken",
)
def test_local_recheck_confirms_failure(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """A bot-blocked URL that definitively fails from the build's vantage
    point is reported broken, with the build's own evidence rather than
    the service's.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    _mock_submit_check(
        responses,
        [
            _checked_url(
                "https://example.com/page",
                status="blocked",
                status_code=403,
                error="403 Forbidden",
            ),
            _checked_url("https://www.lsst.io/"),
        ],
    )
    _mock_local_recheck(responses, "https://example.com/page", status=404)

    app.build()

    # A confirmed failure is a broken link, so it fails the build.
    assert app.statuscode == 1

    status_output = app.status.getvalue()
    assert "blocked: 0" in status_output
    assert "broken: 1" in status_output

    # The evidence is the build's own observation, not the service's.
    message = _warning_message(app, "broken: https://example.com/page")
    assert "HTTP 404" in message
    assert "404 Client Error" in message
    assert "403 Forbidden" not in message
    assert "likely bot protection" not in message


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-recheck-scope",
)
def test_local_recheck_only_visits_blocked_urls(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """Only the bot-blocked URLs are rechecked. Every other URL — ok,
    redirected, or otherwise — keeps the service's verdict and is never
    requested from the build.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    _mock_submit_check(
        responses,
        [
            _checked_url(
                "https://example.com/page",
                status="blocked",
                status_code=403,
                error="403 Forbidden",
            ),
            _checked_url("https://www.lsst.io/"),
            _checked_url(
                "https://example.org/resource",
                status="redirected",
                status_code=200,
                redirect_status_code=301,
                redirect_url="https://example.org/moved",
            ),
        ],
    )
    _mock_local_recheck(responses, "https://example.com/page", status=200)

    app.build()

    # Ook's submit and poll, then exactly one local request.
    assert [call.request.url for call in responses.calls] == [
        f"{OOK_BASE_URL}/linkcheck/checks",
        f"{OOK_BASE_URL}/linkcheck/checks/{OOK_CHECK_ID}",
        "https://example.com/page",
    ]

    status_output = app.status.getvalue()
    assert (
        "Rechecking bot-blocked URLs from this build's own vantage point"
        in status_output
    )
    assert "Local recheck: 1 verified, 0 still blocked, 0 failing" in (
        status_output
    )
    # The redirected URL is untouched by the recheck.
    assert "redirected: 1" in status_output
    assert "redirects to https://example.org/moved" in status_output


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-contribute",
)
def test_local_recheck_contributes_results(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """In a GitHub Actions job that can mint an id token, the local
    observations are contributed back to the service in exactly one POST,
    attested by an OIDC token minted for the service's own base URL and
    described by the run's advisory environment block.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    _set_actions_oidc_env(monkeypatch)
    _mock_submit_check(
        responses,
        [
            _checked_url(
                "https://example.com/page",
                status="blocked",
                status_code=403,
                error="403 Forbidden",
            ),
            _checked_url("https://www.lsst.io/"),
        ],
    )
    _mock_local_recheck(responses, "https://example.com/page", status=200)
    _mock_oidc_token(responses)
    responses.post(
        CONTRIBUTIONS_URL,
        json=_contribution_report(
            accepted=[{"url": "https://example.com/page", "status": "ok"}]
        ),
        status=200,
    )

    app.build()

    assert app.statuscode == 0

    # Ook's submit and poll, the local recheck, the id token, then exactly
    # one contribution POST. The token is minted for the service's own
    # base URL, which is what scopes it to this one deployment.
    audience = quote(OOK_BASE_URL, safe="")
    assert [call.request.url for call in responses.calls] == [
        f"{OOK_BASE_URL}/linkcheck/checks",
        f"{OOK_BASE_URL}/linkcheck/checks/{OOK_CHECK_ID}",
        "https://example.com/page",
        f"{OIDC_TOKEN_ENDPOINT}?api-version=2.0&audience={audience}",
        CONTRIBUTIONS_URL,
    ]

    contribution = responses.calls[-1].request
    # The ingress is Gafaelfawr-protected, so the existing bearer token
    # rides along with the id token in the body.
    assert contribution.headers["Authorization"] == "Bearer test-token"
    assert contribution.body is not None
    payload = json.loads(contribution.body)
    assert payload["id_token"] == "a.b.c"
    assert payload["environment"] == {
        "provider": "github_actions",
        "repository": "lsst-sqre/documenteer",
        "run_url": "https://github.com/lsst-sqre/documenteer/actions/runs/42",
        "checker_version": f"documenteer {__version__}",
    }
    # The batch carries the build's own observation of the blocked URL,
    # and only that URL.
    assert len(payload["results"]) == 1
    result = payload["results"][0]
    assert result["url"] == "https://example.com/page"
    assert result["status_code"] == 200
    assert result["error"] is None
    assert result["checked_at"] is not None

    # What the service did with the batch is reported.
    assert "Contributed 1 link-check result" in app.status.getvalue()


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-contribute-rejected",
)
def test_contribution_rejections_reported(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """Every local observation is contributed — the URL the build resolved
    and the one it was blocked from alike — and an entry the service
    declines is reported per URL with its reason, leaving the build's own
    result untouched.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    _set_actions_oidc_env(monkeypatch)
    _mock_submit_check(
        responses,
        [
            _checked_url(
                "https://example.com/page",
                status="blocked",
                status_code=403,
                error="403 Forbidden",
            ),
            _checked_url(
                "https://example.org/resource",
                status="blocked",
                status_code=403,
                error="403 Forbidden",
            ),
            _checked_url("https://www.lsst.io/"),
        ],
    )
    _mock_local_recheck(responses, "https://example.com/page", status=200)
    _mock_local_recheck(responses, "https://example.org/resource", status=403)
    _mock_oidc_token(responses)
    responses.post(
        CONTRIBUTIONS_URL,
        json=_contribution_report(
            accepted=[{"url": "https://example.com/page", "status": "ok"}],
            rejected=[
                {
                    "url": "https://example.org/resource",
                    "reason": "not_blocked",
                    "message": "Ook resolved this URL itself.",
                }
            ],
        ),
        status=200,
    )

    app.build()

    assert app.statuscode == 0

    contribution = responses.calls[-1].request
    assert contribution.body is not None
    contributed = {
        result["url"]: result
        for result in json.loads(contribution.body)["results"]
    }
    # The batch carries what the build observed for both blocked URLs: the
    # service treats a contributed failure exactly as it treats one of its
    # own checks, so a still-blocked URL is worth sending too.
    assert set(contributed) == {
        "https://example.com/page",
        "https://example.org/resource",
    }
    assert contributed["https://example.com/page"]["status_code"] == 200
    assert contributed["https://example.org/resource"]["status_code"] == 403
    assert contributed["https://example.org/resource"]["error"] is not None

    status_output = app.status.getvalue()
    assert (
        "Contributed 2 link-check results to lsst-sqre/documenteer "
        "(1 accepted, 1 rejected)" in status_output
    )
    # The declined entry is named, with the reason and the service's
    # explanation.
    assert (
        "Contribution rejected for https://example.org/resource "
        "(not_blocked): Ook resolved this URL itself." in status_output
    )

    # A rejection is the service declining an improvement, not a problem
    # with the documentation: it is never a warning, and the build's own
    # merged report is unaffected.
    assert "Contribution rejected" not in app.warning.getvalue()
    assert "ok: 2" in status_output
    assert "blocked: 1" in status_output


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-contribute-no-oidc",
)
def test_contribution_skipped_without_oidc(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """Outside a workflow job that can mint an id token — a laptop build,
    or a workflow that never asked for ``id-token: write`` — there is
    nothing to attest a contribution with, so it is skipped with an info
    note naming the permission. The recheck still informs this build's own
    report, and nothing about the skip touches the build's result.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    # The autouse fixture leaves the Actions id-token variables unset.
    _mock_submit_check(
        responses,
        [
            _checked_url(
                "https://example.com/page",
                status="blocked",
                status_code=403,
                error="403 Forbidden",
            ),
            _checked_url("https://www.lsst.io/"),
        ],
    )
    _mock_local_recheck(responses, "https://example.com/page", status=200)

    app.build()

    # A contribution that was never possible costs the build nothing.
    assert app.statuscode == 0

    # Ook's submit and poll and the local recheck: no token request, no
    # contribution POST.
    assert [call.request.url for call in responses.calls] == [
        f"{OOK_BASE_URL}/linkcheck/checks",
        f"{OOK_BASE_URL}/linkcheck/checks/{OOK_CHECK_ID}",
        "https://example.com/page",
    ]

    # The skip is announced at info level, naming the permission that
    # would supply the token — the one thing an operator can act on.
    message = _status_message(app, "Not contributing")
    assert "id-token: write" in message
    assert "Not contributing" not in app.warning.getvalue()

    # The recheck still informed the report: the blocked URL is verified.
    status_output = app.status.getvalue()
    assert "Local recheck: 1 verified, 0 still blocked, 0 failing" in (
        status_output
    )
    assert "blocked: 0" in status_output
    assert "ok: 2" in status_output


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-contribute-failed",
)
def test_contribution_failure_warns_without_failing_build(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """A service that keeps answering 502 outlasts the retry ladder. The
    contribution is given up on with a warning, and the build — whose own
    report the recheck already informed — is unaffected.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    _set_actions_oidc_env(monkeypatch)
    # The retry ladder's backoff is real time this test has no use for.
    monkeypatch.setattr(
        "documenteer.storage.linkcheckclient.time.sleep", lambda _: None
    )
    _mock_submit_check(
        responses,
        [
            _checked_url(
                "https://example.com/page",
                status="blocked",
                status_code=403,
                error="403 Forbidden",
            ),
            _checked_url("https://www.lsst.io/"),
        ],
    )
    _mock_local_recheck(responses, "https://example.com/page", status=200)
    _mock_oidc_token(responses)
    # The 502 the service documents as retryable: it could not fetch
    # GitHub's signing keys to verify the id token.
    responses.post(CONTRIBUTIONS_URL, json={"detail": "JWKS"}, status=502)

    app.build()

    # A contribution that could not be delivered never fails the build.
    assert app.statuscode == 0

    # The original attempt plus three retries.
    contribution_calls = [
        call
        for call in responses.calls
        if call.request.url == CONTRIBUTIONS_URL
    ]
    assert len(contribution_calls) == 4

    message = _warning_message(app, "Could not contribute")
    assert "4 attempts" in message
    assert "The build is unaffected." in message

    # The local recheck's verdict still stands in this build's report.
    status_output = app.status.getvalue()
    assert "blocked: 0" in status_output
    assert "ok: 2" in status_output


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-contribute-malformed",
)
def test_contribution_unreadable_response_warns(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """A contribution the service accepts but answers with a body this
    release cannot read is a warning, not a crash.

    Ook is deployed independently of Documenteer, so a 200 can carry a
    shape a given release does not know. That must land in the same place
    as every other contribution failure — a warning, with the build's own
    report intact — rather than escaping as an unhandled validation error.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    _set_actions_oidc_env(monkeypatch)
    _mock_submit_check(
        responses,
        [
            _checked_url(
                "https://example.com/page",
                status="blocked",
                status_code=403,
                error="403 Forbidden",
            ),
            _checked_url("https://www.lsst.io/"),
        ],
    )
    _mock_local_recheck(responses, "https://example.com/page", status=200)
    _mock_oidc_token(responses)
    responses.post(CONTRIBUTIONS_URL, json={"unexpected": "shape"}, status=200)

    app.build()

    assert app.statuscode == 0

    # An unreadable body reads no better on a resend, so the contribution
    # is given up on after the one POST.
    contribution_calls = [
        call
        for call in responses.calls
        if call.request.url == CONTRIBUTIONS_URL
    ]
    assert len(contribution_calls) == 1

    message = _warning_message(app, "Could not contribute")
    assert "ContributionReport" in message
    assert "The build is unaffected." in message

    # The local recheck's verdict still stands in this build's report.
    status_output = app.status.getvalue()
    assert "blocked: 0" in status_output
    assert "ok: 2" in status_output


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-contribute-nothing",
)
def test_no_blocked_urls_contributes_nothing(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """A check with no blocked URLs has nothing to recheck and so nothing
    to contribute: even in a workflow job that could mint one, no id token
    is requested. Most builds take this path, so it must stay free.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    _set_actions_oidc_env(monkeypatch)
    _mock_submit_check(
        responses,
        [
            _checked_url(url)
            for url in ("https://example.com/page", "https://www.lsst.io/")
        ],
    )

    app.build()

    assert app.statuscode == 0
    assert [call.request.url for call in responses.calls] == [
        f"{OOK_BASE_URL}/linkcheck/checks",
        f"{OOK_BASE_URL}/linkcheck/checks/{OOK_CHECK_ID}",
    ]


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-warningiserror-blocked",
    warningiserror=True,
    # The test root is not a Git repository, so sphinx-last-updated-by-git
    # warns; suppress it to isolate link-check reporting under -W.
    confoverrides={"suppress_warnings": ["git"]},
)
def test_blocked_passes_warningiserror(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """With warnings-as-errors (Sphinx's ``-W``), a check that reports a
    blocked link (no broken) still exits 0, because blocked is reported at
    info level rather than as a warning — including the local recheck that
    finds the URL blocked from the build's vantage point too.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    _mock_submit_check(
        responses,
        [
            _checked_url(
                "https://example.com/page",
                status="blocked",
                status_code=403,
                error="403 Forbidden",
            ),
            _checked_url("https://www.lsst.io/"),
        ],
    )
    _mock_local_recheck(responses, "https://example.com/page", status=403)

    # Under warningiserror, any logger.warning would raise SphinxWarning;
    # info-level reporting keeps the build green.
    app.build()

    assert app.statuscode == 0
    assert "blocked: 1" in app.status.getvalue()


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-blocked-artifact",
)
def test_blocked_link_json_artifact(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """The JSON artifact records the blocked disposition: the summary
    carries a ``blocked`` count and the per-URL result keeps its
    ``blocked`` status and diagnostic detail, flagged as one the build
    rechecked for itself.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    _mock_submit_check(
        responses,
        [
            _checked_url(
                "https://example.com/page",
                status="blocked",
                status_code=403,
                error="403 Forbidden",
            ),
            _checked_url("https://www.lsst.io/"),
        ],
    )
    _mock_local_recheck(responses, "https://example.com/page", status=403)

    app.build()

    data = json.loads((Path(app.outdir) / "linkcheck.json").read_text())
    assert data["summary"]["blocked"] == 1

    results = {url["url"]: url for url in data["urls"]}
    blocked = results["https://example.com/page"]
    assert blocked["status"] == "blocked"
    assert blocked["status_code"] == 403
    assert blocked["error"] == "403 Forbidden"
    assert blocked["pages"] == ["index"]
    assert blocked["locally_rechecked"] is True

    # A URL the service settled on its own is not flagged as rechecked.
    assert results["https://www.lsst.io/"]["locally_rechecked"] is False


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-recheck-artifact",
)
def test_local_recheck_json_artifact_merged(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """The JSON artifact carries the merged view: a locally verified URL
    is recorded ok, with the build's own evidence and the redirect it
    resolved through, and the summary counts move with it.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    _mock_submit_check(
        responses,
        [
            _checked_url(
                "https://example.com/page",
                status="blocked",
                status_code=403,
                error="403 Forbidden",
            ),
            _checked_url("https://www.lsst.io/"),
        ],
    )
    responses.head(
        "https://example.com/page",
        status=302,
        headers={"Location": "https://example.com/moved"},
    )
    responses.head("https://example.com/moved", status=200)

    app.build()

    data = json.loads((Path(app.outdir) / "linkcheck.json").read_text())
    assert data["summary"]["blocked"] == 0
    assert data["summary"]["ok"] == 2

    results = {url["url"]: url for url in data["urls"]}
    verified = results["https://example.com/page"]
    assert verified["status"] == "ok"
    assert verified["status_code"] == 200
    assert verified["error"] is None
    assert verified["redirect_status_code"] == 302
    assert verified["redirect_url"] == "https://example.com/moved"
    assert verified["locally_rechecked"] is True
    # The pages the URL occurs on survive the merge.
    assert verified["pages"] == ["index"]


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-warningiserror-broken",
    warningiserror=True,
    # The test root is not a Git repository, so sphinx-last-updated-by-git
    # warns; suppress it so only the broken-link warning can raise under -W.
    confoverrides={"suppress_warnings": ["git"]},
)
def test_broken_fails_warningiserror(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """A broken link still fails the build under warnings-as-errors: the
    broken result is reported as a warning and sets a nonzero exit status.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    _mock_submit_check(
        responses,
        [
            _checked_url(
                "https://example.com/page",
                status="broken",
                status_code=404,
                error="404 Not Found",
            ),
            _checked_url("https://www.lsst.io/"),
        ],
    )

    app.build()

    # Broken links fail the build under -W, both via _set_failure_status
    # and because the broken result is reported as a warning.
    assert app.statuscode == 1
    assert (
        "broken: https://example.com/page (page: index)"
        in app.warning.getvalue()
    )


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-unreachable",
)
def test_unreachable_service_degrades(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """An unreachable Ook service degrades gracefully by default: the
    build warns that the link check was skipped and exits 0.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    # No mocked responses are registered, so the submission raises a
    # connection error (the responses mock also blocks real network
    # access, standing in for an unreachable service).

    app.build()

    assert app.statuscode == 0
    warning_output = app.warning.getvalue()
    assert "Link check skipped" in warning_output
    assert "Could not reach the Ook link-check service" in warning_output

    # A guide is invited to turn on strict mode through the TOML key that
    # actually governs it in its own configuration file.
    message = _warning_message(app, "Link check skipped")
    assert "[sphinx.linkcheck] strict = true in documenteer.toml" in message


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-no-token",
)
def test_missing_token_falls_back_to_builtin(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """A missing OOK_TOKEN (e.g. a fork's PR build, where secrets are
    unavailable) falls back to Sphinx's built-in in-process link checker
    rather than skipping, so link checking still runs. The service is
    never contacted (the client's token guard raises first).
    """
    monkeypatch.delenv("OOK_TOKEN", raising=False)
    _mock_builtin_head_ok(responses, TESTROOT_EXTERNAL_URLS)

    app.build()

    # The built-in checker ran and every link resolved, so the build
    # exits 0 — not the old silent skip, which also exited 0 but checked
    # nothing (the broken-link test below proves the check really runs).
    assert app.statuscode == 0

    # The Ook service is never contacted without a token.
    assert not any(
        (call.request.url or "").startswith(OOK_BASE_URL)
        for call in responses.calls
    )

    # The built-in checker wrote its own report; the service artifact was
    # not written.
    assert (Path(app.outdir) / "output.txt").is_file()
    assert not (Path(app.outdir) / "linkcheck.json").exists()

    # The fallback is announced at info level (in the status stream), so a
    # warnings-as-errors (-W) build does not fail on it.
    status_output = app.status.getvalue()
    assert "falling back to Sphinx's built-in" in status_output
    assert "No Ook API token is available" in status_output
    assert "falling back" not in app.warning.getvalue()


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-no-token-broken",
)
def test_missing_token_fallback_reports_broken_links(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """The built-in fallback really checks links: a broken link found by
    the in-process checker fails the build with a nonzero exit status,
    proving the fallback is not a silent no-op.
    """
    monkeypatch.delenv("OOK_TOKEN", raising=False)
    # One link is broken (404 on both HEAD and the built-in's GET retry);
    # the others resolve.
    responses.head("https://example.com/page", status=404)
    responses.get("https://example.com/page", status=404)
    responses.head("https://www.lsst.io/", status=200)
    responses.head("https://example.org/resource", status=200)

    app.build()

    # The built-in fallback found a broken link, so the build fails — a
    # silent skip would have exited 0.
    assert app.statuscode == 1
    assert (Path(app.outdir) / "output.txt").is_file()
    assert not (Path(app.outdir) / "linkcheck.json").exists()


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-rejected-token",
)
def test_rejected_token_falls_back_to_builtin(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """A rejected OOK_TOKEN (the service returns 401 on submit) falls back
    to Sphinx's built-in in-process link checker, the same as a missing
    token: the submission is attempted, rejected, and the build then runs
    the built-in check.
    """
    monkeypatch.setenv("OOK_TOKEN", "bad-token")
    # The service rejects the submission...
    responses.post(f"{OOK_BASE_URL}/linkcheck/checks", status=401)
    # ...so the build falls back to the built-in in-process checker.
    _mock_builtin_head_ok(responses, TESTROOT_EXTERNAL_URLS)

    app.build()

    assert app.statuscode == 0

    # The submission was attempted (and rejected) before falling back.
    service_calls = [
        call
        for call in responses.calls
        if (call.request.url or "").startswith(OOK_BASE_URL)
    ]
    assert len(service_calls) == 1
    assert service_calls[0].request.method == "POST"

    # The built-in checker wrote its own report; no service artifact.
    assert (Path(app.outdir) / "output.txt").is_file()
    assert not (Path(app.outdir) / "linkcheck.json").exists()

    # The fallback is announced at info level.
    assert "falling back to Sphinx's built-in" in app.status.getvalue()


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-no-token-wording",
)
def test_guide_fallback_names_documenteer_toml(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """A guide's built-in fallback names the TOML key, in the file the
    guide actually has, that selects the built-in builder explicitly.
    """
    monkeypatch.delenv("OOK_TOKEN", raising=False)
    _mock_builtin_head_ok(responses, TESTROOT_EXTERNAL_URLS)

    app.build()

    message = _status_message(app, "falling back to Sphinx's built-in")
    assert "[sphinx.linkcheck] use_service = false in documenteer.toml" in (
        message
    )


@pytest.mark.skipif(
    not _HAS_TECHNOTE_DEPS, reason="technote dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="technote-linkcheck-service",
    srcdir="technote-linkcheck-service-no-token",
)
def test_technote_fallback_names_conf_py(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """A technote's built-in fallback names the conf.py setting that
    selects the built-in builder, not a ``documenteer.toml`` key in a file
    the technote does not have.
    """
    monkeypatch.delenv("OOK_TOKEN", raising=False)
    # The technote's linkcheck_ignore drops https://ls.st/, so the
    # built-in checker requests only the other two links.
    _mock_builtin_head_ok(
        responses, ["https://example.com/page", "https://www.lsst.io/"]
    )

    app.build()

    # Falling back is still the success path: the built-in check ran and
    # every link resolved.
    assert app.statuscode == 0

    message = _status_message(app, "falling back to Sphinx's built-in")
    assert "documenteer_linkcheck_use_service = False in conf.py" in message
    assert "documenteer.toml" not in message


@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service-bare",
    srcdir="linkcheck-service-bare-no-token",
    confoverrides={
        "documenteer_linkcheck_origin_base_url": "https://example.lsst.io"
    },
)
def test_bare_fallback_names_conf_py(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """A project configured from ``conf.py`` alone is pointed at the
    conf.py setting, naming no TOML file it does not have.
    """
    monkeypatch.delenv("OOK_TOKEN", raising=False)
    _mock_builtin_head_ok(responses, ["https://example.com/page"])

    app.build()

    assert app.statuscode == 0

    message = _status_message(app, "falling back to Sphinx's built-in")
    assert "documenteer_linkcheck_use_service = False in conf.py" in message
    assert "documenteer.toml" not in message
    assert "technote.toml" not in message


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-poll-budget",
    confoverrides={"documenteer_linkcheck_poll_budget": 0},
)
def test_poll_budget_exhaustion_degrades(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """A check that does not complete within the polling budget degrades
    gracefully by default: the build warns that the link check was
    skipped and exits 0.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    check_url = f"{OOK_BASE_URL}/linkcheck/checks/{OOK_CHECK_ID}"
    pending_urls = [
        _checked_url(
            "https://example.com/page",
            status="pending",
            status_code=None,
            checked_at=None,
        )
    ]
    responses.post(
        f"{OOK_BASE_URL}/linkcheck/checks",
        json=_check_response(pending_urls, status="pending"),
        status=202,
        headers={"Location": check_url},
    )
    # The check never completes: every poll returns the pending check.
    responses.get(
        check_url,
        json=_check_response(pending_urls, status="pending"),
        status=200,
    )

    app.build()

    assert app.statuscode == 0
    warning_output = app.warning.getvalue()
    assert "Link check skipped" in warning_output
    assert "did not complete" in warning_output
    assert "polling budget" in warning_output


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-strict-unreachable",
    confoverrides={"documenteer_linkcheck_strict": True},
)
def test_unreachable_service_strict_fails(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """With [sphinx.linkcheck] strict = true, an unreachable Ook service
    fails the build with a nonzero exit instead of degrading.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    # No mocked responses are registered, so the submission raises a
    # connection error (the responses mock also blocks real network
    # access, standing in for an unreachable service).

    app.build()

    assert app.statuscode == 1
    warning_output = app.warning.getvalue()
    assert "Link check failed" in warning_output
    assert "Could not reach the Ook link-check service" in warning_output

    # A guide is told about the TOML key that actually governs strict
    # mode in its own configuration file.
    message = _warning_message(app, "Link check failed")
    assert "[sphinx.linkcheck] strict = true in documenteer.toml" in message


@pytest.mark.skipif(
    not _HAS_TECHNOTE_DEPS, reason="technote dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="technote-linkcheck-service",
    srcdir="technote-linkcheck-service-strict-unreachable",
    confoverrides={"documenteer_linkcheck_strict": True},
)
def test_technote_strict_failure_names_conf_py(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """A technote's strict-mode failure names the conf.py setting that
    turned strict mode on, not a TOML key that does not exist.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    # No mocked responses are registered, so the submission raises a
    # connection error, standing in for an unreachable service.

    app.build()

    # Strict mode still fails the build, exactly as for a guide.
    assert app.statuscode == 1

    message = _warning_message(app, "Link check failed")
    assert "documenteer_linkcheck_strict = True in conf.py" in message
    assert "documenteer.toml" not in message


@pytest.mark.skipif(
    not _HAS_TECHNOTE_DEPS, reason="technote dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="technote-linkcheck-service",
    srcdir="technote-linkcheck-service-unreachable",
)
def test_technote_skip_names_conf_py(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """A technote's non-strict skip message — the one that actively
    invites the author to act — points at the conf.py setting rather than
    a file the technote does not have.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    # No mocked responses are registered, so the submission raises a
    # connection error, standing in for an unreachable service.

    app.build()

    # Degrading gracefully still exits zero, exactly as for a guide.
    assert app.statuscode == 0

    message = _warning_message(app, "Link check skipped")
    assert "documenteer_linkcheck_strict = True in conf.py" in message
    assert "documenteer.toml" not in message


@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service-bare",
    srcdir="linkcheck-service-bare-unreachable",
    confoverrides={
        "documenteer_linkcheck_origin_base_url": "https://example.lsst.io"
    },
)
def test_bare_skip_names_conf_py(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """A project configured from ``conf.py`` alone is pointed at the
    conf.py strict setting, naming no TOML file it does not have.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    # No mocked responses are registered, so the submission raises a
    # connection error, standing in for an unreachable service.

    app.build()

    assert app.statuscode == 0

    message = _warning_message(app, "Link check skipped")
    assert "documenteer_linkcheck_strict = True in conf.py" in message
    assert "documenteer.toml" not in message
    assert "technote.toml" not in message


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-strict-no-token",
    confoverrides={"documenteer_linkcheck_strict": True},
)
def test_missing_token_strict_falls_back(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """With [sphinx.linkcheck] strict = true and no OOK_TOKEN, the build
    still falls back to Sphinx's built-in in-process checker rather than
    hard-failing: a missing token means the project isn't using the
    service, so strict (which governs genuine service problems) does not
    apply. The exit status comes from the built-in's real link results.
    """
    monkeypatch.delenv("OOK_TOKEN", raising=False)
    _mock_builtin_head_ok(responses, TESTROOT_EXTERNAL_URLS)

    app.build()

    # Falls back and the built-in finds every link ok, so the build exits
    # 0 even under strict — strict no longer hard-fails on a missing token.
    assert app.statuscode == 0
    assert (Path(app.outdir) / "output.txt").is_file()
    assert not (Path(app.outdir) / "linkcheck.json").exists()

    # It fell back rather than reporting a strict service failure.
    assert "falling back to Sphinx's built-in" in app.status.getvalue()
    assert "Link check failed" not in app.warning.getvalue()


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-strict-poll-budget",
    confoverrides={
        "documenteer_linkcheck_strict": True,
        "documenteer_linkcheck_poll_budget": 0,
    },
)
def test_poll_budget_exhaustion_strict_fails(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """With [sphinx.linkcheck] strict = true, poll-budget exhaustion
    fails the build with a nonzero exit instead of degrading.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    check_url = f"{OOK_BASE_URL}/linkcheck/checks/{OOK_CHECK_ID}"
    pending_urls = [
        _checked_url(
            "https://example.com/page",
            status="pending",
            status_code=None,
            checked_at=None,
        )
    ]
    responses.post(
        f"{OOK_BASE_URL}/linkcheck/checks",
        json=_check_response(pending_urls, status="pending"),
        status=202,
        headers={"Location": check_url},
    )
    # The check never completes: every poll returns the pending check.
    responses.get(
        check_url,
        json=_check_response(pending_urls, status="pending"),
        status=200,
    )

    app.build()

    assert app.statuscode == 1
    warning_output = app.warning.getvalue()
    assert "Link check failed" in warning_output
    assert "did not complete" in warning_output
    assert "polling budget" in warning_output


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-escape-hatch",
    confoverrides={"documenteer_linkcheck_use_service": False},
)
def test_use_service_false_restores_builtin_builder(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """With [sphinx.linkcheck] use_service = false, the service builder
    override is not applied and Sphinx's built-in linkcheck builder runs:
    links are checked in-process and the Ook service is never contacted.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")

    # The override fell through to the stock builder, not the
    # service-backed subclass.
    assert type(app.builder) is CheckExternalLinksBuilder

    # The responses mock intercepts the in-process link checks, so no
    # real network access happens during the build.
    app.build()

    # The Ook service was never contacted.
    assert not any(
        (call.request.url or "").startswith(OOK_BASE_URL)
        for call in responses.calls
    )

    # The stock builder wrote its own report, not the service artifact.
    assert (Path(app.outdir) / "output.txt").is_file()
    assert not (Path(app.outdir) / "linkcheck.json").exists()


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-response-pages",
)
def test_report_pages_from_response_origin_paths(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """The pages reported for each link come from the poll response's
    ``origin_paths``, not a locally-held submission-to-page map.

    The single-page test root references every URL only from ``index``,
    so page names other than ``index`` can only have come from the
    response.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    _mock_submit_check(
        responses,
        [
            _checked_url(
                "https://example.com/page",
                status="broken",
                status_code=404,
                error="404 Not Found",
                origin_paths=["contributing", "release-notes"],
            ),
            _checked_url(
                "https://www.lsst.io/",
                origin_paths=["release-notes"],
            ),
        ],
    )

    app.build()

    # The broken link's detail line lists the pages from the response,
    # not the local "index" the root actually references it from.
    warning_output = app.warning.getvalue()
    assert (
        "broken: https://example.com/page "
        "(page: contributing, release-notes)" in warning_output
    )

    # The JSON artifact sources each URL's pages from the response too.
    data = json.loads((Path(app.outdir) / "linkcheck.json").read_text())
    results = {url["url"]: url for url in data["urls"]}
    assert results["https://example.com/page"]["pages"] == [
        "contributing",
        "release-notes",
    ]
    assert results["https://www.lsst.io/"]["pages"] == ["release-notes"]
    # The artifact keeps its shape: a ``pages`` key, not the model's raw
    # ``origin_paths`` field.
    assert "origin_paths" not in results["https://example.com/page"]


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-artifact",
)
def test_json_artifact(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """A machine-readable JSON artifact with the full per-URL results is
    written to the build output directory.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    _mock_submit_check(
        responses,
        [
            _checked_url(
                "https://example.com/page",
                status="redirected",
                status_code=200,
                redirect_status_code=301,
                redirect_url="https://example.com/new-page",
            ),
            _checked_url(
                "https://www.lsst.io/",
                status="broken",
                status_code=404,
                error="404 Not Found",
            ),
            _checked_url("https://example.org/resource"),
        ],
    )

    app.build()

    artifact_path = Path(app.outdir) / "linkcheck.json"
    assert artifact_path.is_file()
    data = json.loads(artifact_path.read_text())

    assert data["id"] == OOK_CHECK_ID
    assert data["status"] == "complete"
    assert data["summary"] == {
        "pending": 0,
        "ok": 1,
        "redirected": 1,
        "failing": 0,
        "broken": 1,
        "unsupported": 0,
        "blocked": 0,
    }

    results = {url["url"]: url for url in data["urls"]}

    redirected = results["https://example.com/page"]
    assert redirected["status"] == "redirected"
    assert redirected["status_code"] == 200
    assert redirected["redirect_status_code"] == 301
    assert redirected["redirect_url"] == "https://example.com/new-page"
    assert redirected["pages"] == ["index"]

    broken = results["https://www.lsst.io/"]
    assert broken["status"] == "broken"
    assert broken["status_code"] == 404
    assert broken["error"] == "404 Not Found"
    assert broken["pages"] == ["index"]

    ok = results["https://example.org/resource"]
    assert ok["status"] == "ok"
    assert ok["status_code"] == 200
    assert ok["pages"] == ["index"]

    # The status output points at the artifact.
    assert "linkcheck.json" in app.status.getvalue()


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service-multipage",
    srcdir="linkcheck-service-multipage",
)
def test_multipage_url_submits_all_pages(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """A URL referenced from multiple pages is submitted with every
    referencing docname in ``origin_paths`` (deduplicated, sorted), not
    just the first occurrence Sphinx's built-in collector records.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    # Ook returns the canonical (fragment-stripped) URL for the fragment
    # link, mirroring the real service.
    _mock_submit_check(
        responses,
        [
            _checked_url("https://example.com/shared"),
            _checked_url("https://example.com/guide"),
            _checked_url("https://example.org/only-a"),
        ],
    )

    app.build()

    assert app.statuscode == 0

    api_request = responses.calls[0].request
    assert api_request.body is not None
    payload = json.loads(api_request.body)
    submitted = {url["url"]: url["origin_paths"] for url in payload["urls"]}

    # The shared URL, referenced from both pages, is submitted with both
    # docnames in sorted order.
    assert submitted["https://example.com/shared"] == ["page-a", "page-b"]
    # A URL with a fragment is submitted verbatim (fragment retained) and
    # still carries every referencing page.
    assert submitted["https://example.com/guide#intro"] == [
        "page-a",
        "page-b",
    ]
    # A single-page URL still lists just its one page.
    assert submitted["https://example.org/only-a"] == ["page-a"]


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service-multipage",
    srcdir="linkcheck-service-multipage-artifact",
)
def test_multipage_url_artifact_pages(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """The JSON artifact lists every referencing page for each URL,
    sourced from the poll response's per-URL ``origin_paths``.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    # Ook echoes each URL's referencing pages back in origin_paths,
    # returning the fragment-stripped canonical URL for the submitted
    # https://example.com/guide#intro.
    _mock_submit_check(
        responses,
        [
            _checked_url(
                "https://example.com/shared",
                origin_paths=["page-a", "page-b"],
            ),
            _checked_url(
                "https://example.com/guide",
                origin_paths=["page-a", "page-b"],
            ),
            _checked_url(
                "https://example.org/only-a", origin_paths=["page-a"]
            ),
        ],
    )

    app.build()

    data = json.loads((Path(app.outdir) / "linkcheck.json").read_text())
    results = {url["url"]: url for url in data["urls"]}

    # A URL referenced from both pages lists both, from origin_paths.
    assert results["https://example.com/shared"]["pages"] == [
        "page-a",
        "page-b",
    ]
    # The canonical URL Ook returns carries every referencing page in its
    # origin_paths, even though the submitted URL had a #fragment.
    assert results["https://example.com/guide"]["pages"] == [
        "page-a",
        "page-b",
    ]
    # A single-page URL lists just its one page.
    assert results["https://example.org/only-a"]["pages"] == ["page-a"]
