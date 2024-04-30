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


def test_extend_excludes_for_non_index_source() -> None:
    ipynb_demo_dir = Path(__file__).parent.joinpath("../demo/ipynb-technote")

    # Initial excludes
    excludes = ["_build", "_static", "_templates", "conf.py", "README.rst"]

    extend_excludes_for_non_index_source(excludes, "ipynb", ipynb_demo_dir)

    assert "subdir/subdir-notebook.ipynb" in excludes
    assert "extra-notebook.ipynb" in excludes
    assert "index.ipynb" not in excludes
