"""Test the documenteer.toml configuration support."""

from __future__ import annotations

from typing import Dict, List, Tuple, Union

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
nitpick_ignore = [
    ["py:class", "pydantic.main.BaseModel"]
]
nitpick_ignore_regex = [
    ["py:.+", 'fastapi\\..+']
]

[sphinx.intersphinx.projects]
sphinx = "https://www.sphinx-doc.org/en/master/"
documenteer = "https://documenteer.lsst.io"
python = "https://docs.python.org/3/"

[sphinx.linkcheck]
ignore = [
    "^https://confluence.lsstcorp.org/"
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

EXAMPLE_SIDEBARS = """

[project]
title = "Documenteer"
copyright = "2022 AURA"

[project.python]
package = "documenteer"

[sphinx]
disable_primary_sidebars = [
    "index",
    "changelog",
]
"""


def test_load() -> None:
    config = DocumenteerConfig.load(EXAMPLE)
    assert config.project == "Documenteer"
    assert config.base_url == "https://documenteer.lsst.io"
    assert config.copyright == "2022 AURA"
    assert config.github_url == "https://github.com/lsst-sqre/documenteer"
    assert config.version == "1.0.0"
    assert config.automodapi_toctreedirm == "api"


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


def test_append_intersphinx_projects() -> None:
    config = DocumenteerConfig.load(EXAMPLE)

    projects: Dict[str, Tuple[str, Union[str, None]]] = {
        "python": ("https://docs.python.org/3/", None),
    }
    config.extend_intersphinx_mapping(projects)
    assert projects == {
        "python": ("https://docs.python.org/3/", None),
        "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
        "documenteer": ("https://documenteer.lsst.io", None),
    }


def test_append_linkcheck_ignore() -> None:
    config = DocumenteerConfig.load(EXAMPLE)

    linkcheck_ignore = [
        r"^https://jira.lsstcorp.org/browse/",
        r"^https://ls.st/",
    ]
    config.append_linkcheck_ignore(linkcheck_ignore)
    assert linkcheck_ignore == [
        r"^https://jira.lsstcorp.org/browse/",
        r"^https://ls.st/",
        r"^https://confluence.lsstcorp.org/",
    ]


def test_disable_primary_sidebars_defaults() -> None:
    """Test sphinx.disable_primary_sidebars defaults where it wasn't set."""
    config = DocumenteerConfig.load(EXAMPLE)
    html_sidebars: Dict[str, List[str]] = {}
    config.disable_primary_sidebars(html_sidebars)
    assert html_sidebars == {"index": []}


def test_disable_primary_sidebars() -> None:
    """Test sphinx.disable_primary_sidebars."""
    config = DocumenteerConfig.load(EXAMPLE_SIDEBARS)
    html_sidebars: Dict[str, List[str]] = {}
    config.disable_primary_sidebars(html_sidebars)
    assert html_sidebars == {"index": [], "changelog": []}
