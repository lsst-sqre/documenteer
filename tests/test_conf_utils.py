"""Test the documenteer.conf.utils module."""

from __future__ import annotations

import pytest
from sphinx.errors import ConfigError

from documenteer.conf import get_asset_path


def test_get_asset_path() -> None:
    result = get_asset_path("rubin-titlebar-imagotype-light.svg")
    assert result.endswith("rubin-titlebar-imagotype-light.svg")

    # This asset doesn't exist
    with pytest.raises(ConfigError):
        get_asset_path("_missing.svg")
