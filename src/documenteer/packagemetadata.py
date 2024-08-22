"""Utilties for getting metadata about packages."""

from __future__ import annotations

import re
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version

__all__ = [
    "get_package_version_str",
    "PackageNotFoundError",
    "Semver",
    "get_package_version_semver",
]

SEMVER_PATTERN = re.compile(
    r"^(?P<major>[0-9]+)"
    r"\.(?P<minor>[0-9]+)"
    r"\.(?P<patch>[0-9]+)"
    r"(-(?P<pre>[a-zA-Z0-9\.]+))?"
    r"(\+(?P<build>[a-zA-Z0-9\.]+))?"
)


def get_package_version_str(package_name: str) -> str:
    """Get an installed Python package's version, as a string."""
    return version(package_name)


@dataclass
class Semver:
    """A representation of a semantic version."""

    major: int = 0

    minor: int = 0

    patch: int = 0

    prerelease: str | None = None

    build: str | None = None

    @classmethod
    def parse(cls, version_string: str) -> Semver:
        version_string = version_string.lstrip("v")
        match = SEMVER_PATTERN.match(version_string)
        if not match:
            raise ValueError(
                "Version {version_string} is not a semantic version"
            )
        return cls(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
            prerelease=match.group("pre"),
            build=match.group("build"),
        )

    @property
    def _version_tuple(self) -> tuple[int, int, int]:
        return (self.major, self.minor, self.patch)

    def __gt__(self, other: Semver) -> bool:
        # FIXME this comparison ignore pre-release/build info
        return self._version_tuple > other._version_tuple

    def __lt__(self, other: Semver) -> bool:
        # FIXME this comparison ignore pre-release/build info
        return self._version_tuple < other._version_tuple

    def __ge__(self, other: Semver) -> bool:
        # FIXME this comparison ignore pre-release/build info
        return self._version_tuple >= other._version_tuple

    def __le__(self, other: Semver) -> bool:
        # FIXME this comparison ignore pre-release/build info
        return self._version_tuple <= other._version_tuple


def get_package_version_semver(package_name: str) -> Semver:
    """Get a parsed representation of a package's version, assuming it is a
    semantic version.
    """
    version_str = get_package_version_str(package_name)
    return Semver.parse(version_str)
