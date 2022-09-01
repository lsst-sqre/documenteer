"""Test the documenteer.toml configuration support."""

from __future__ import annotations

from documenteer.conf import DocumenteerConfig

EXAMPLE = """

[project]
title = "Documenteer"
canonical_url = "https://documenteer.lsst.io"

[project.python]
package = "documenteer"
"""


def test_load() -> None:
    config = DocumenteerConfig.load(EXAMPLE)
    assert config.project == "Documenteer"
    assert config.canonical_url == "https://documenteer.lsst.io"
