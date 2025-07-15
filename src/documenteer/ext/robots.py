"""Sphinx extension for automatically generating robots.txt files.

This extension automatically creates and inserts a robots.txt file into the
built HTML site if no such robots.txt file already exists and if a sitemap.xml
file does exist in the built site. In the generated robots.txt file, it links
to the sitemap using the Sphinx html_baseurl configuration value.
"""

from __future__ import annotations

from pathlib import Path

from sphinx.application import Sphinx
from sphinx.util import logging
from sphinx.util.typing import ExtensionMetadata

from ..version import __version__

__all__ = ["generate_robots_txt", "setup"]

logger = logging.getLogger(__name__)


def generate_robots_txt(app: Sphinx, exception: Exception | None) -> None:
    """Generate a robots.txt file automatically if conditions are met.

    Parameters
    ----------
    app
        The Sphinx application.
    exception
        Exception raised during build, if any. If not None, the function
        returns early without generating robots.txt.

    Notes
    -----
    This function is called during the build-finished Sphinx event.
    It generates a robots.txt file if:

    1. No robots.txt file already exists in the output directory
    2. A sitemap.xml file exists in the output directory
    3. The html_baseurl configuration is set
    """
    # Don't generate robots.txt if the build failed
    if exception is not None:
        return

    # Only generate for HTML builders
    if app.builder.name != "html":
        return

    outdir = Path(app.outdir)
    robots_path = outdir / "robots.txt"
    sitemap_path = outdir / "sitemap.xml"

    # Check if robots.txt already exists
    if robots_path.exists():
        logger.debug("robots.txt already exists, skipping generation")
        return

    # Check if sitemap.xml exists
    if not sitemap_path.exists():
        logger.debug("sitemap.xml not found, skipping robots.txt generation")
        return

    # Get the base URL from configuration
    base_url = getattr(app.config, "html_baseurl", None)
    if not base_url:
        logger.debug(
            "html_baseurl not configured, skipping robots.txt generation"
        )
        return

    # Ensure base URL ends with /
    if not base_url.endswith("/"):
        base_url += "/"

    # Generate robots.txt content
    robots_content = f"""User-agent: *

Sitemap: {base_url}sitemap.xml
"""

    # Write robots.txt file
    try:
        robots_path.write_text(robots_content, encoding="utf-8")
        logger.info(f"Generated robots.txt at {robots_path}")
    except OSError as e:
        logger.warning(f"Failed to write robots.txt: {e}")


def setup(app: Sphinx) -> ExtensionMetadata:
    """Set up the robots extension.

    Parameters
    ----------
    app
        The Sphinx application.

    Returns
    -------
    ExtensionMetadata
        Extension metadata for Sphinx.
    """
    # Connect to the build-finished event
    app.connect("build-finished", generate_robots_txt)

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
