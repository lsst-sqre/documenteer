"""Sphinx extensions to mock Python code reference roles.

These roles are useful for temporarily adding semantically-markedup
APIs while waiting for the API reference itself to be added.
"""

import logging

from docutils import nodes

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def mock_code_ref_role(
    name, rawtext, text, lineno, inliner, options=None, content=None
):
    options = options or {}
    content = content or []
    if text.startswith("~"):
        text = text.lstrip("~").split(".")[-1]
    node = nodes.literal(text=text)
    return [node], []


def setup(app):
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
