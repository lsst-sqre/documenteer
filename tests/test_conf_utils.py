"""Test the documenteer.conf.utils module."""

from __future__ import annotations

from pathlib import Path

import pytest
from sphinx.errors import ConfigError

from documenteer.conf import (
    extend_excludes_for_non_index_source,
    get_asset_path,
    get_template_dir,
)
from documenteer.conf._utils import get_technote_origin_base_url


def test_get_asset_path() -> None:
    result = get_asset_path("rubin-titlebar-imagotype-light.svg")
    assert result.endswith("rubin-titlebar-imagotype-light.svg")

    # This asset doesn't exist
    with pytest.raises(ConfigError):
        get_asset_path("_missing.svg")


def test_get_template_dir() -> None:
    result = get_template_dir("pydata")
    assert result.endswith("pydata")

    # This template dir doesn't exist
    with pytest.raises(ConfigError):
        get_asset_path("not-a-theme")


def test_technote_origin_from_canonical_url() -> None:
    """The technote origin base URL prefers the canonical URL from
    technote.toml, normalized (lowercased host, trailing slash
    stripped).
    """
    assert (
        get_technote_origin_base_url(
            canonical_url="https://SQR-000.lsst.io/",
            technote_id="SQR-000",
        )
        == "https://sqr-000.lsst.io"
    )


def test_technote_origin_from_handle() -> None:
    """Without a canonical URL, the technote origin base URL is derived
    from the technote handle as ``https://<handle>.lsst.io``.
    """
    assert (
        get_technote_origin_base_url(
            canonical_url=None,
            technote_id="SQR-000",
        )
        == "https://sqr-000.lsst.io"
    )


def test_technote_origin_unavailable() -> None:
    """Without a canonical URL or a technote handle, the origin base URL
    is None.
    """
    assert (
        get_technote_origin_base_url(canonical_url=None, technote_id=None)
        is None
    )


def test_extend_excludes_for_non_index_source() -> None:
    ipynb_demo_dir = Path(__file__).parent.joinpath("../demo/ipynb-technote")

    # Initial excludes
    excludes = ["_build", "_static", "_templates", "conf.py", "README.rst"]

    extend_excludes_for_non_index_source(excludes, "ipynb", ipynb_demo_dir)

    assert "subdir/subdir-notebook.ipynb" in excludes
    assert "extra-notebook.ipynb" in excludes
    assert "index.ipynb" not in excludes
