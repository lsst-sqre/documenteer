"""Tests for the documenteer.sphinxconfig.stackconf module.
"""

from documenteer.sphinxconfig.stackconf import (
    _insert_eups_version,
    _insert_single_package_eups_version,
)


def test_eups_version_daily(monkeypatch):
    with monkeypatch.context() as m:
        m.setenv("EUPS_TAG", "d_2019_02_08")
        import os

        print(os.getenv("EUPS_TAG"))
        c = {}
        c = _insert_eups_version(c)

    assert c["release_eups_tag"] == "d_2019_02_08"
    assert c["release_git_ref"] == "master"
    assert c["version"] == "d_2019_02_08"
    assert c["release"] == "d_2019_02_08"
    assert c["scipipe_conda_ref"] == "master"
    assert c["pipelines_demo_ref"] == "master"
    assert c["newinstall_ref"] == "master"


def test_eups_version_weekly(monkeypatch):
    with monkeypatch.context() as m:
        m.setenv("EUPS_TAG", "w_2019_05")
        c = {}
        c = _insert_eups_version(c)

    assert c["release_eups_tag"] == "w_2019_05"
    assert c["release_git_ref"] == "w.2019.05"
    assert c["version"] == "w_2019_05"
    assert c["release"] == "w_2019_05"
    assert c["scipipe_conda_ref"] == "w.2019.05"
    assert c["pipelines_demo_ref"] == "w.2019.05"
    assert c["newinstall_ref"] == "w.2019.05"


def test_eups_version_major(monkeypatch):
    with monkeypatch.context() as m:
        m.setenv("EUPS_TAG", "v17_0")
        c = {}
        c = _insert_eups_version(c)

    assert c["release_eups_tag"] == "v17_0"
    assert c["release_git_ref"] == "17.0"
    assert c["version"] == "v17_0"
    assert c["release"] == "v17_0"
    assert c["scipipe_conda_ref"] == "17.0"
    assert c["pipelines_demo_ref"] == "17.0"
    assert c["newinstall_ref"] == "17.0"


def test_eups_version_rc(monkeypatch):
    with monkeypatch.context() as m:
        m.setenv("EUPS_TAG", "v17_0_rc1")
        c = {}
        c = _insert_eups_version(c)

    assert c["release_eups_tag"] == "v17_0_rc1"
    assert c["release_git_ref"] == "17.0.rc1"
    assert c["version"] == "v17_0_rc1"
    assert c["release"] == "v17_0_rc1"
    assert c["scipipe_conda_ref"] == "17.0.rc1"
    assert c["pipelines_demo_ref"] == "17.0.rc1"
    assert c["newinstall_ref"] == "17.0.rc1"


def test_eups_version_single_package(monkeypatch):
    version_string = "pkgversion"
    with monkeypatch.context() as m:
        m.delenv("EUPS_TAG", raising=False)
        c = {}
        c = _insert_single_package_eups_version(c, version_string)

    assert c["release_eups_tag"] == "current"
    assert c["release_git_ref"] == "master"
    assert c["version"] == version_string
    assert c["release"] == version_string
    assert c["scipipe_conda_ref"] == "master"
    assert c["pipelines_demo_ref"] == "master"
    assert c["newinstall_ref"] == "master"
