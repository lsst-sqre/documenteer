"""Tests for the documenteer.services.technoteread module."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
from docutils import nodes
from sphinx.util.docutils import (
    additional_nodes,
    register_node,
    unregister_node,
)

import documenteer.conf
from documenteer.services.technoteread import TechnoteReadError, read_technote

CONF_PY = "from documenteer.conf.technote import *  # noqa: F401,F403\n"

TOML = """\
[technote]
id = "SQR-000"
series_id = "SQR"
"""

TITLED_TOML = TOML + 'title = "A Title Declared in TOML"\n'

RST = """\
#############
Demo technote
#############

.. abstract::

   A technote is a web-native single page document.

Introduction
============

Body text.
"""


def write_technote(
    root: Path,
    *,
    toml: str = TOML,
    filename: str | None = "index.rst",
    content: str = RST,
    conf: str | None = CONF_PY,
) -> Path:
    """Write a technote source directory, returning its path."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "technote.toml").write_text(toml)
    if conf is not None:
        (root / "conf.py").write_text(conf)
    if filename is not None:
        (root / filename).write_text(content)
    return root


PROCESS_STATE_PROBE = """\
import json
import sys
from pathlib import Path

from docutils.parsers.rst import directives, roles
from sphinx.util import docutils as sphinx_docutils

from documenteer.services.technoteread import read_technote


def rebound(before, after):
    return sorted(
        name
        for name in set(before) | set(after)
        if before.get(name) is not after.get(name)
    )


before_directives = dict(directives._directives)
before_roles = dict(roles._roles)
before_nodes = set(sphinx_docutils.additional_nodes)

read_technote(Path(sys.argv[1]))

print(
    json.dumps(
        {
            "directives": rebound(before_directives, directives._directives),
            "roles": rebound(before_roles, roles._roles),
            "nodes": sorted(
                node.__name__
                for node in before_nodes
                ^ set(sphinx_docutils.additional_nodes)
            ),
            "attributes": [
                f"{package}.{attribute}"
                for package, attribute in (
                    ("documenteer.conf", "technote"),
                    ("technote", "sphinxconf"),
                )
                if hasattr(sys.modules.get(package), attribute)
            ],
        }
    )
)
"""
"""A script reporting what one technote read leaves behind in a process.

It runs in an interpreter of its own, because a fresh process is the only
place "as it found it" is a question: within the test session an earlier
Sphinx build has usually registered the same directives, roles, and node
classes already, and an earlier read has usually imported the configuration
modules.
"""


def test_title_resolves_from_the_document_heading(tmp_path: Path) -> None:
    """A technote that declares no title is titled by its H1."""
    root = write_technote(tmp_path)

    document = read_technote(root)

    assert document.title == "Demo technote"
    assert document.metadata.title == "Demo technote"
    assert document.metadata.id == "SQR-000"


def test_toml_title_wins_over_the_heading(tmp_path: Path) -> None:
    """A title declared in technote.toml is never overridden by the H1."""
    root = write_technote(tmp_path, toml=TITLED_TOML)

    assert read_technote(root).title == "A Title Declared in TOML"


def test_doctree_carries_the_parsed_document(tmp_path: Path) -> None:
    """The read returns the root document's doctree."""
    root = write_technote(tmp_path)

    doctree = read_technote(root).doctree

    titles = [node.astext() for node in doctree.findall(nodes.title)]
    assert titles[0] == "Demo technote"
    assert "web-native" in doctree.astext()


def test_read_leaves_the_technote_directory_untouched(tmp_path: Path) -> None:
    """No build output, doctree cache, or environment is left behind."""
    root = write_technote(tmp_path)
    before = sorted(p.name for p in root.iterdir())

    read_technote(root)

    assert sorted(p.name for p in root.iterdir()) == before


def test_markdown_technote_is_read(tmp_path: Path) -> None:
    """A MyST Markdown technote reads like a reStructuredText one."""
    root = write_technote(
        tmp_path,
        filename="index.md",
        content="# Markdown technote\n\n```{abstract}\nA summary.\n```\n",
    )

    assert read_technote(root).title == "Markdown technote"


def test_notebook_technote_is_read_without_executing_it(
    tmp_path: Path,
) -> None:
    """A notebook technote is read for its markup, never executed."""
    notebook = json.dumps(
        {
            "cells": [
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": "# Notebook technote\n\n"
                    "```{abstract}\nA summary.\n```",
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    # Executing the notebook would raise; reading it must not.
                    "source": "raise RuntimeError('the notebook ran')",
                },
            ],
            "metadata": {},
            "nbformat": 4,
            "nbformat_minor": 5,
        }
    )
    root = write_technote(tmp_path, filename="index.ipynb", content=notebook)

    assert read_technote(root).title == "Notebook technote"


def test_missing_index_is_reported(tmp_path: Path) -> None:
    """A technote with no content file names the files it could have had.

    Sphinx reports a missing root document by embedding the technote
    package's traceback in its message, which is not what a person running
    the command needs to read.
    """
    root = write_technote(tmp_path, filename=None)

    with pytest.raises(TechnoteReadError) as excinfo:
        read_technote(root)

    message = str(excinfo.value)
    assert "index.rst, index.md, index.ipynb" in message
    assert "Traceback" not in message


def test_missing_conf_py_is_reported(tmp_path: Path) -> None:
    """A directory Sphinx cannot configure names the missing conf.py."""
    root = write_technote(tmp_path, conf=None)

    with pytest.raises(TechnoteReadError) as excinfo:
        read_technote(root)

    assert "conf.py" in str(excinfo.value)


def test_missing_technote_toml_is_reported(tmp_path: Path) -> None:
    """A directory with no technote.toml is not a technote to read."""
    root = tmp_path / "empty"
    root.mkdir()
    (root / "conf.py").write_text(CONF_PY)
    (root / "index.rst").write_text(RST)

    with pytest.raises(TechnoteReadError) as excinfo:
        read_technote(root)

    assert "technote.toml" in str(excinfo.value)


def test_unparseable_notebook_is_reported(tmp_path: Path) -> None:
    """A content file Sphinx cannot parse is an error, not a traceback.

    The parser's own diagnosis is what the error carries; the caller names
    the file it was reading.
    """
    root = write_technote(
        tmp_path, filename="index.ipynb", content="{ not json"
    )

    with pytest.raises(TechnoteReadError) as excinfo:
        read_technote(root)

    assert "JSON" in str(excinfo.value)


def test_repeated_reads_do_not_share_configuration(tmp_path: Path) -> None:
    """Two technotes read in one process each get their own settings.

    A technote's ``conf.py`` gets its Sphinx settings from modules that
    compute them once, at import, from the current directory — and Python
    imports a module once per process. Each read therefore gets its own
    import of them, or the second technote would be built with the first
    one's configuration.
    """
    first = write_technote(tmp_path / "first")
    second = write_technote(
        tmp_path / "second",
        toml='[technote]\nid = "SQR-001"\n',
        content="#######\nSecond\n#######\n\n.. abstract::\n\n   Two.\n",
    )

    assert read_technote(first).title == "Demo technote"
    assert read_technote(second).title == "Second"
    assert read_technote(second).metadata.id == "SQR-001"


def test_read_restores_the_import_state_it_found(tmp_path: Path) -> None:
    """A read leaves the process's imported modules as it found them.

    Anything else in the process that builds a technote — another Sphinx
    build, a test suite — keeps the configuration it imported, rather than
    silently inheriting the settings of whatever technote was read along the
    way.
    """
    root = write_technote(tmp_path)
    names = ("documenteer.conf.technote", "technote.sphinxconf")
    before = {name: sys.modules.get(name) for name in names}

    read_technote(root)

    assert {name: sys.modules.get(name) for name in names} == before


def test_read_leaves_the_process_state_it_found(tmp_path: Path) -> None:
    """A read leaves docutils' registries and the config packages alone.

    A Sphinx build registers its extensions' directives, roles, and node
    classes in docutils' process-global registries, and a technote's
    ``conf.py`` binds the configuration modules it imports on their parent
    packages. Neither is this read's to keep: the process that ran it goes on
    to do other things.
    """
    root = write_technote(tmp_path)

    result = subprocess.run(
        [sys.executable, "-c", PROCESS_STATE_PROBE, str(root)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "directives": [],
        "roles": [],
        "nodes": [],
        "attributes": [],
    }


def test_read_keeps_node_classes_registered_before_it(tmp_path: Path) -> None:
    """Node classes registered before the read outlive it.

    Sphinx's own `~sphinx.util.docutils.docutils_namespace` unregisters
    *every* node in ``additional_nodes`` on the way out rather than the ones
    the enclosed build added, so wrapping the read in it would take a
    caller's nodes down with the technote's.
    """

    class SentinelNode(nodes.Element):
        """A node class standing in for one the caller registered."""

    root = write_technote(tmp_path)
    register_node(SentinelNode)
    try:
        read_technote(root)

        assert SentinelNode in additional_nodes
        assert hasattr(nodes.GenericNodeVisitor, "visit_SentinelNode")
    finally:
        unregister_node(SentinelNode)
        additional_nodes.discard(SentinelNode)


def test_read_puts_back_a_preimported_config_module(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A config module imported before the read is what its package carries.

    A stand-in module is enough to tell: the read takes the name out of the
    import cache and puts it back, and never looks inside.
    """
    root = write_technote(tmp_path)
    preimported = ModuleType("documenteer.conf.technote")
    monkeypatch.setitem(sys.modules, "documenteer.conf.technote", preimported)
    monkeypatch.setattr(
        documenteer.conf, "technote", preimported, raising=False
    )

    read_technote(root)

    assert sys.modules["documenteer.conf.technote"] is preimported
    assert sys.modules["documenteer.conf"].technote is preimported
