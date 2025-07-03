"""Sphinx extensions to mock Python code reference roles.

These roles are useful for temporarily adding semantically-markedup
APIs while waiting for the API reference itself to be added.
"""

from __future__ import annotations

import logging
from typing import Any

from docutils import nodes
from docutils.parsers.rst.states import Inliner
from sphinx.application import Sphinx
from sphinx.util.typing import ExtensionMetadata

from ..version import __version__

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def mock_code_ref_role(
    name: str,
    rawtext: str,
    text: str,
    lineno: int,
    inliner: Inliner,
    options: dict[str, Any] | None = None,
    content: bool | None = None,
) -> tuple[list[nodes.Node], list[nodes.system_message]]:
    """Process a mock code reference role."""
    options = options or {}
    if text.startswith("~"):
        text = text.lstrip("~").split(".")[-1]
    node = nodes.literal(text=text)
    return [node], []


def setup(app: Sphinx) -> ExtensionMetadata:
    """Set up the mock code reference roles."""
    # Reference roles from the Python domain
    original_roles = (
        "data",
        "exc",
        "func",
        "class",
        "const",
        "attr",
        "meth",
        "mod",
        "obj",
    )
    for rolename in original_roles:
        mock_name = "l" + rolename
        app.add_role(mock_name, mock_code_ref_role)

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
