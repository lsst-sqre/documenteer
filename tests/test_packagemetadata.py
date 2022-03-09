"""Tests for the packagemetadata module."""

from __future__ import annotations

from documenteer.packagemetadata import Semver, get_package_version_semver


def test_semver_parse() -> None:
    v = Semver.parse("2.1.0")
    assert v == Semver(major=2, minor=1, patch=0)

    v = Semver.parse("2.1.0-alpha.1")
    assert v == Semver(major=2, minor=1, patch=0, prerelease="alpha.1")

    v = Semver.parse("2.1.0-alpha.1+b1")
    assert v == Semver(
        major=2, minor=1, patch=0, prerelease="alpha.1", build="b1"
    )

    assert Semver.parse("2.0.0") == Semver.parse("2.0.0")
    assert Semver.parse("2.0.0") >= Semver.parse("2.0.0")
    assert Semver.parse("2.0.0") > Semver.parse("1.0.0")
    assert Semver.parse("1.0.0") < Semver.parse("2.0.0")
    assert Semver.parse("1.0.0") <= Semver.parse("2.0.0")


def test_get_package_version_semver() -> None:
    assert isinstance(get_package_version_semver("sphinx-jinja"), Semver)
