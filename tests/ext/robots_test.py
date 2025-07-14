# type: ignore
"""Tests for documenteer.ext.robots."""

from __future__ import annotations

import pytest
from sphinx.testing.util import SphinxTestApp


@pytest.mark.sphinx(
    "html",
    testroot="robots-sitemap",
)
def test_robots_txt_with_sitemap(app: SphinxTestApp) -> None:
    """Test robots.txt generation when sitemap.xml exists."""
    app.build()

    # Check that both files exist
    robots_path = app.outdir / "robots.txt"
    sitemap_path = app.outdir / "sitemap.xml"

    assert sitemap_path.exists(), "sitemap.xml should be generated"
    assert robots_path.exists(), "robots.txt should be generated"

    # Check robots.txt content
    content = robots_path.read_text()
    assert "User-agent: *" in content
    assert "Sitemap: https://project.lsst.io/sitemap.xml" in content


@pytest.mark.sphinx(
    "html",
    testroot="robots-nositemap",
)
def test_robots_txt_without_sitemap(app: SphinxTestApp) -> None:
    """Test robots.txt is not generated when sitemap.xml doesn't exist."""
    app.build()

    # Check that robots.txt is not created when sitemap doesn't exist
    robots_path = app.outdir / "robots.txt"
    sitemap_path = app.outdir / "sitemap.xml"

    assert not sitemap_path.exists(), "sitemap.xml should not be generated"
    assert not robots_path.exists(), "robots.txt should not be generated"
