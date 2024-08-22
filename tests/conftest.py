"""Pytest configuration."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest_plugins = ["sphinx.testing.fixtures"]

# Exclude 'roots' dirs for pytest test collector
collect_ignore: list[str] = ["roots"]


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "sphinx(builder, testroot='name'): Run sphinx on a site"
    )


@pytest.fixture(scope="session")
def rootdir() -> Path:
    """Directory containing Sphinx projects for testing (`str`)."""
    return Path(__file__).parent.absolute() / "roots"
