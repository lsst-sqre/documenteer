"""Test the documenteer.toml configuration support."""

from __future__ import annotations

from documenteer.conf import DocumenteerConfig

EXAMPLE = """

[project]
title = "Documenteer"
base_url = "https://documenteer.lsst.io"
copyright = "2022 AURA"
github_url = "https://github.com/lsst-sqre/documenteer"

[project.python]
package = "documenteer"
"""


def test_load() -> None:
    config = DocumenteerConfig.load(EXAMPLE)
    assert config.project == "Documenteer"
    assert config.base_url == "https://documenteer.lsst.io"
    assert config.copyright == "2022 AURA"
    assert config.github_url == "https://github.com/lsst-sqre/documenteer"
