"""Tests for documenteer.designdocs.ddconfig"""

from datetime import datetime

import pytest

from documenteer.sphinxconfig.technoteconf import _build_confs, read_git_branch


@pytest.fixture()
def sample_metadata():
    m = {
        "series": "SQR",
        "serial_number": "000",
        "doc_id": "SQR-000",
        "doc_title": "The Title",
        "authors": ["Jonathan Sick"],
        "last_revised": "2015-11-23",
        "version": "1.0.0",
        "copyright": "2016 AURA/LSST",
        "description": "Description",
        "url": "https://repo.example.org",
        "docushare_url": None,
        "github_url": "https://example.org/org/repo",
    }
    return m


@pytest.mark.parametrize("branch_name", ["master", "tickets/DM-0000"])
def test_git_version(monkeypatch, mocker, sample_metadata, branch_name):
    monkeypatch.setenv("TRAVIS", "false")
    import documenteer.sphinxconfig.technoteconf

    documenteer.sphinxconfig.technoteconf.read_git_branch = mocker.MagicMock()
    documenteer.sphinxconfig.technoteconf.read_git_branch.return_value = (
        branch_name
    )

    sample_metadata.pop("version")

    config = _build_confs(sample_metadata)

    assert config["version"] == branch_name


@pytest.mark.parametrize(
    "input,expected", [(datetime(2016, 7, 1), "2016-07-01")]
)
def test_git_last_revised(
    monkeypatch, mocker, sample_metadata, input, expected
):
    monkeypatch.setenv("TRAVIS", "false")
    import documenteer.sphinxconfig.technoteconf as technoteconf

    technoteconf.get_project_content_commit_date = mocker.MagicMock()
    technoteconf.get_project_content_commit_date.return_value = input

    sample_metadata.pop("last_revised")

    config = _build_confs(sample_metadata)

    assert config["today"] == expected
    assert config["html_context"]["last_revised"] == expected


def test_hard_coded_version(monkeypatch, sample_metadata):
    monkeypatch.setenv("TRAVIS", "false")
    config = _build_confs(sample_metadata)
    assert config["version"] == sample_metadata["version"]


def test_hard_coded_last_revised(monkeypatch, sample_metadata):
    monkeypatch.setenv("TRAVIS", "false")
    config = _build_confs(sample_metadata)
    assert (
        config["html_context"]["last_revised"]
        == sample_metadata["last_revised"]
    )


def test_branch_name_on_travis(monkeypatch, sample_metadata):
    monkeypatch.setenv("TRAVIS", "true")
    monkeypatch.setenv("TRAVIS_BRANCH", "my-travis-branch")

    b = read_git_branch()
    assert b == "my-travis-branch"
