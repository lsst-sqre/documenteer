from typing import List

import pytest
from sphinx.testing.path import path

pytest_plugins = ("sphinx.testing.fixtures",)

# Exclude 'roots' dirs for pytest test collector
collect_ignore: List[str] = ["roots"]


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "sphinx(builder, testroot='name'): Run sphinx on a site"
    )


@pytest.fixture(scope="session")
def rootdir() -> path:
    """Directory containing Sphinx projects for testing (`str`)."""
    return path(__file__).parent.abspath() / "roots"
