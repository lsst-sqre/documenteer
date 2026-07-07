"""Tests for the documenteer.ext.linkcheckservice extension."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest
import pytest_responses  # noqa: F401
from responses import RequestsMock
from sphinx.builders.linkcheck import CheckExternalLinksBuilder
from sphinx.testing.util import SphinxTestApp

from documenteer.ext.linkcheckservice import resolve_default_branch_flag

# Whether the guide preset's dependencies are importable; the test root
# builds the full user-guide stack (``from documenteer.conf.guide import *``).
_HAS_GUIDE_DEPS = importlib.util.find_spec("pydata_sphinx_theme") is not None

# Whether the technote preset's dependencies are importable; the technote
# test root builds the full technote stack
# (``from documenteer.conf.technote import *``).
_HAS_TECHNOTE_DEPS = importlib.util.find_spec("technote") is not None

OOK_BASE_URL = "https://roundtable.lsst.cloud/ook"


def _checked_url(url: str, status: str = "ok", **overrides: Any) -> dict:
    """Create a per-URL result for a mocked Ook link-check response."""
    result: dict[str, Any] = {
        "url": url,
        "status": status,
        "status_code": 200 if status == "ok" else None,
        "redirect_status_code": None,
        "redirect_url": None,
        "error": None,
        "checked_at": "2026-07-06T12:00:00Z",
    }
    result.update(overrides)
    return result


def _check_response(
    urls: list[dict], *, check_id: int = 7, status: str = "complete"
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
    responses: RequestsMock, urls: list[dict], *, check_id: int = 7
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


def _mock_submit_check_completed(
    responses: RequestsMock, urls: list[dict], *, check_id: int = 7
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
    assert poll_request.url == f"{OOK_BASE_URL}/linkcheck/checks/7"

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
    assert "Link check complete (Ook check id: 7)" in status_output
    assert "ok: 3" in status_output


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
    assert "Link check complete (Ook check id: 7)" in status_output
    assert "ok: 2" in status_output


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
    assert "Link check complete (Ook check id: 7)" in status_output
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
def test_warning_statuses_pass_build(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """Redirected, failing, and unsupported links produce warnings only
    and the build exits 0; redirect locations appear in the summary.
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

    # Warning-only statuses do not fail the build.
    assert app.statuscode == 0

    # The status counts cover each warning-only status.
    status_output = app.status.getvalue()
    assert "redirected: 1" in status_output
    assert "failing: 1" in status_output
    assert "unsupported: 1" in status_output

    # Each link needing attention is warned about, with its page, HTTP
    # status, and redirect location where applicable.
    warning_output = app.warning.getvalue()
    assert (
        "redirected: https://example.com/page (page: index)" in warning_output
    )
    assert "redirects to https://example.com/new-page (HTTP 301)" in (
        warning_output
    )
    assert "failing: https://www.lsst.io/ (page: index)" in warning_output
    assert "HTTP 503" in warning_output
    assert "503 Service Unavailable" in warning_output
    assert "unsupported: https://example.org/resource (page: index)" in (
        warning_output
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


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-no-token",
)
def test_missing_token_degrades(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """A missing OOK_TOKEN (e.g. a fork's PR build, where secrets are
    unavailable) degrades gracefully by default: the build warns that the
    link check was skipped and exits 0, without contacting the service.
    """
    monkeypatch.delenv("OOK_TOKEN", raising=False)

    app.build()

    assert app.statuscode == 0
    warning_output = app.warning.getvalue()
    assert "Link check skipped" in warning_output
    assert "No Ook API token is available" in warning_output
    assert "OOK_TOKEN" in warning_output

    # The service is never contacted without a token.
    assert len(responses.calls) == 0


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
    check_url = f"{OOK_BASE_URL}/linkcheck/checks/7"
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


@pytest.mark.skipif(
    not _HAS_GUIDE_DEPS, reason="guide dependencies are not installed"
)
@pytest.mark.sphinx(
    "linkcheck",
    testroot="linkcheck-service",
    srcdir="linkcheck-service-strict-no-token",
    confoverrides={"documenteer_linkcheck_strict": True},
)
def test_missing_token_strict_fails(
    app: SphinxTestApp, responses: RequestsMock, monkeypatch: Any
) -> None:
    """With [sphinx.linkcheck] strict = true, a missing OOK_TOKEN fails
    the build with a nonzero exit instead of degrading.
    """
    monkeypatch.delenv("OOK_TOKEN", raising=False)

    app.build()

    assert app.statuscode == 1
    warning_output = app.warning.getvalue()
    assert "Link check failed" in warning_output
    assert "No Ook API token is available" in warning_output


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
    check_url = f"{OOK_BASE_URL}/linkcheck/checks/7"
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

    assert data["id"] == 7
    assert data["status"] == "complete"
    assert data["summary"] == {
        "pending": 0,
        "ok": 1,
        "redirected": 1,
        "failing": 0,
        "broken": 1,
        "unsupported": 0,
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
