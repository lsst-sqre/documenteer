"""Test the documenteer.toml configuration support."""

from __future__ import annotations

import pytest
from sphinx.errors import ConfigError

from documenteer.conf import DocumenteerConfig

EXAMPLE = """

[project]
title = "Documenteer"
base_url = "https://documenteer.lsst.io"
copyright = "2022 AURA"
github_url = "https://github.com/lsst-sqre/documenteer"
version = "1.0.0"

[sphinx]
extensions = [
    "sphinx_design",
    "new_extension",
]
"""

EXAMPLE_BAD_PACKAGE = """
[project]
title = "Documenteer"
base_url = "https://documenteer.lsst.io"
copyright = "2022 AURA"
github_url = "https://github.com/lsst-sqre/documenteer"

[project.python]
package = "notapackage"
"""

EXAMPLE_PYTHON = """

[project]
title = "Documenteer"
copyright = "2022 AURA"

[project.python]
package = "documenteer"
"""


def test_load() -> None:
    config = DocumenteerConfig.load(EXAMPLE)
    assert config.project == "Documenteer"
    assert config.base_url == "https://documenteer.lsst.io"
    assert config.copyright == "2022 AURA"
    assert config.github_url == "https://github.com/lsst-sqre/documenteer"
    assert config.version == "1.0.0"


def test_bad_package() -> None:
    with pytest.raises(ConfigError):
        DocumenteerConfig.load(EXAMPLE_BAD_PACKAGE)


def test_python_metadata() -> None:
    config = DocumenteerConfig.load(EXAMPLE_PYTHON)
    assert config.project == "Documenteer"
    assert config.base_url == "https://documenteer.lsst.io"
    assert config.copyright == "2022 AURA"
    assert config.github_url == "https://github.com/lsst-sqre/documenteer"
    assert isinstance(config.version, str)


def test_append_extensions() -> None:
    """Test DocumenteerConfig.append_extensions()."""
    config = DocumenteerConfig.load(EXAMPLE)

    existing_extensions = [
        "sphinx_design",
        "sphinx.ext.autodoc",
        "documenteer.sphinxext",
    ]
    config.append_extensions(existing_extensions)
    assert existing_extensions == [
        "sphinx_design",
        "sphinx.ext.autodoc",
        "documenteer.sphinxext",
        "new_extension",
    ]
