"""Pytest configuration."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest_plugins = ["sphinx.testing.fixtures"]

# Exclude 'roots' dirs for pytest test collector
collect_ignore: list[str] = ["roots"]


@pytest.fixture(scope="session")
def rootdir() -> Path:
    """Directory containing Sphinx projects for testing (`str`)."""
    return Path(__file__).parent.absolute() / "roots"
