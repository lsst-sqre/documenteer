"""Test the documenteer.conf.utils module."""

from __future__ import annotations

import pytest
from sphinx.errors import ConfigError

from documenteer.conf import get_asset_path, get_template_dir


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
