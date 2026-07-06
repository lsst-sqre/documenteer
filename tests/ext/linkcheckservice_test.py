"""Tests for the documenteer.ext.linkcheckservice extension."""

from __future__ import annotations

import importlib.util
import json
from typing import Any

import pytest
import pytest_responses  # noqa: F401
from responses import RequestsMock
from sphinx.testing.util import SphinxTestApp

from documenteer.ext.linkcheckservice import resolve_default_branch_flag

# Whether the guide preset's dependencies are importable; the test root
# builds the full user-guide stack (``from documenteer.conf.guide import *``).
_HAS_GUIDE_DEPS = importlib.util.find_spec("pydata_sphinx_theme") is not None

OOK_BASE_URL = "https://roundtable.lsst.cloud/ook"


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
        {
            "url": url,
            "status": "ok",
            "status_code": 200,
            "redirect_status_code": None,
            "redirect_url": None,
            "error": None,
            "checked_at": "2026-07-06T12:00:00Z",
        }
        for url in ("https://example.com/page", "https://www.lsst.io/")
    ]
    responses.post(
        f"{OOK_BASE_URL}/linkcheck/checks",
        json={
            "id": 7,
            "self_url": f"{OOK_BASE_URL}/linkcheck/checks/7",
            "ltd_slug": "example",
            "default_branch": True,
            "status": "complete",
            "date_created": "2026-07-06T12:00:00Z",
            "date_completed": "2026-07-06T12:00:05Z",
            "summary": {"ok": len(checked_urls)},
            "urls": checked_urls,
        },
        status=201,
    )

    app.build()

    # The happy path exits 0.
    assert app.statuscode == 0

    # A single submission was made, with bearer auth from OOK_TOKEN.
    assert len(responses.calls) == 1
    api_request = responses.calls[0].request
    assert api_request.headers["Authorization"] == "Bearer test-token"

    # The submission payload carries the slug derived from base_url's
    # subdomain, the default-branch flag from the GitHub Actions env, and
    # the URL + page-path list.
    assert api_request.body is not None
    payload = json.loads(api_request.body)
    assert payload["ltd_slug"] == "example"
    assert payload["default_branch"] is True
    submitted = {url["url"]: url["paths"] for url in payload["urls"]}
    assert submitted == {
        "https://example.com/page": ["index"],
        "https://www.lsst.io/": ["index"],
    }

    # linkcheck_ignore patterns (the guide preset ignores https://ls.st/)
    # are applied client-side: ignored URLs are never submitted.
    assert not any(url.startswith("https://ls.st/") for url in submitted)

    # A summary is printed.
    status_output = app.status.getvalue()
    assert "Link check complete (Ook check id: 7)" in status_output
    assert "ok: 2" in status_output
