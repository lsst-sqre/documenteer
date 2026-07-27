# type: ignore
"""Tests for documenteer.ext.githubeditlink.

These builds drive ``sphinx.application.Sphinx`` directly rather than through
the ``app`` fixture, because ``SphinxTestApp`` hardcodes ``confdir = srcdir``
and the central case this extension exists for is precisely the build where
they differ (``sphinx-build -c . docs …``).

The whole module requires pydata-sphinx-theme: ``use_edit_page_button`` is that
theme's option, so there is nothing to exercise without it.
"""

from __future__ import annotations

import importlib.util
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import git
import pytest
from git import Repo
from sphinx.application import Sphinx

_HAS_PYDATA = importlib.util.find_spec("pydata_sphinx_theme") is not None

pytestmark = pytest.mark.skipif(
    not _HAS_PYDATA, reason="pydata_sphinx_theme is not installed"
)

CONF_PY = """\
extensions = ["documenteer.ext.githubeditlink"]

html_theme = "pydata_sphinx_theme"
html_theme_options = {"use_edit_page_button": True}
html_context = {
    "github_user": "lsst",
    "github_repo": "dp2_lsst_io",
    "github_version": "main",
}
"""

INDEX_RST = """\
Test page
=========

Body text.
"""

# The URL pydata-sphinx-theme builds for the index page of the project
# configured by CONF_PY, for a source directory in ``docs/``.
DP2_INDEX_URL = "https://github.com/lsst/dp2_lsst_io/edit/main/docs/index.rst"


def _project_warnings(warning_output: str) -> list[str]:
    """Filter a build's warning stream down to warnings about the project.

    Constructing several ``Sphinx`` applications in one process makes Sphinx
    re-register its own node classes, each time emitting a "node class ... is
    already registered" warning. That noise is an artifact of the test process,
    not of the build under test, so it is dropped here.
    """
    return [
        line
        for line in warning_output.splitlines()
        if line.strip() and "is already registered" not in line
    ]


class _Build:
    """The result of a completed Sphinx build."""

    def __init__(self, app: Sphinx, warning_output: str) -> None:
        self.app = app
        self.warnings = _project_warnings(warning_output)

    @property
    def doc_path(self) -> str | None:
        """The ``doc_path`` the extension set, or `None` if it set none."""
        return self.app.config.html_context.get("doc_path")

    @property
    def use_edit_page_button(self) -> bool:
        return self.app.config.html_theme_options["use_edit_page_button"]

    @property
    def index_html(self) -> str:
        return (Path(self.app.outdir) / "index.html").read_text()


def _write_project(*, confdir: Path, srcdir: Path) -> None:
    """Write a minimal Sphinx project with the given config and source dirs.

    The two directories may be the same or different; either way ``conf.py``
    lands in ``confdir`` and ``index.rst`` in ``srcdir``.
    """
    confdir.mkdir(parents=True, exist_ok=True)
    srcdir.mkdir(parents=True, exist_ok=True)
    (confdir / "conf.py").write_text(CONF_PY)
    (srcdir / "index.rst").write_text(INDEX_RST)


def _build(*, confdir: Path, srcdir: Path, outdir: Path) -> _Build:
    """Build a project with Sphinx, capturing its warning stream.

    ``Sphinx.__init__`` emits ``config-inited``, so the extension has already
    run by the time the application is constructed.
    """
    warning = StringIO()
    app = Sphinx(
        srcdir=str(srcdir),
        confdir=str(confdir),
        outdir=str(outdir),
        doctreedir=str(outdir / ".doctrees"),
        buildername="html",
        status=StringIO(),
        warning=warning,
    )
    app.build()
    return _Build(app, warning.getvalue())


def test_confdir_at_repo_root(tmp_path: Path) -> None:
    """The dp2 layout: ``conf.py`` at the repo root, sources in ``docs/``.

    This is ``sphinx-build -c . docs _build/html``. The edit URL must address
    the *source* file, so ``doc_path`` is the source directory's path in the
    working tree -- not the config directory's.
    """
    Repo.init(tmp_path)
    _write_project(confdir=tmp_path, srcdir=tmp_path / "docs")

    build = _build(
        confdir=tmp_path, srcdir=tmp_path / "docs", outdir=tmp_path / "_build"
    )

    assert build.doc_path == "docs"
    # End-to-end: the rendered link addresses docs/index.rst, not ./index.rst.
    assert f'href="{DP2_INDEX_URL}"' in build.index_html


def test_confdir_equals_srcdir_in_subdirectory(tmp_path: Path) -> None:
    """Documenteer's own layout: ``docs/`` is both confdir and srcdir."""
    Repo.init(tmp_path)
    docs = tmp_path / "docs"
    _write_project(confdir=docs, srcdir=docs)

    build = _build(confdir=docs, srcdir=docs, outdir=tmp_path / "_build")

    assert build.doc_path == "docs"
    assert f'href="{DP2_INDEX_URL}"' in build.index_html


def test_srcdir_at_repo_root(tmp_path: Path) -> None:
    """A source directory at the repo root yields an empty ``doc_path``.

    ``Path.relative_to`` reports ``"."`` for this case, which would put a
    literal ``./`` into the URL.
    """
    Repo.init(tmp_path)
    _write_project(confdir=tmp_path, srcdir=tmp_path)

    build = _build(
        confdir=tmp_path, srcdir=tmp_path, outdir=tmp_path / "_build"
    )

    assert build.doc_path == ""
    assert (
        'href="https://github.com/lsst/dp2_lsst_io/edit/main/index.rst"'
        in build.index_html
    )
    assert "/edit/main/./" not in build.index_html


def test_not_a_git_repository(tmp_path: Path) -> None:
    """Outside a Git checkout the button is omitted without failing the build.

    ``GitRepository`` is patched rather than relying on the temporary directory
    being outside a checkout, so the test can't be perturbed by where pytest's
    basetemp lives.
    """
    _write_project(confdir=tmp_path, srcdir=tmp_path / "docs")

    with patch(
        "documenteer.ext.githubeditlink.GitRepository",
        side_effect=git.InvalidGitRepositoryError,
    ):
        build = _build(
            confdir=tmp_path,
            srcdir=tmp_path / "docs",
            outdir=tmp_path / "_build",
        )

    assert build.use_edit_page_button is False
    assert build.doc_path is None
    assert "Edit on GitHub" not in build.index_html
    # Nothing is logged at warning level, so builds using ``-W`` still pass.
    assert build.warnings == []


def test_symlinked_srcdir(tmp_path: Path) -> None:
    """A symlinked path to the project still resolves to the same doc path."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    Repo.init(repo_dir)
    _write_project(confdir=repo_dir, srcdir=repo_dir / "docs")

    link = tmp_path / "link"
    link.symlink_to(repo_dir, target_is_directory=True)

    build = _build(
        confdir=link, srcdir=link / "docs", outdir=tmp_path / "_build"
    )

    assert build.doc_path == "docs"
    assert f'href="{DP2_INDEX_URL}"' in build.index_html


def test_inert_without_edit_page_button(tmp_path: Path) -> None:
    """With the button off, the extension sets nothing (the technote case)."""
    Repo.init(tmp_path)
    _write_project(confdir=tmp_path, srcdir=tmp_path / "docs")
    (tmp_path / "conf.py").write_text(
        CONF_PY.replace(
            '{"use_edit_page_button": True}', '{"use_edit_page_button": False}'
        )
    )

    build = _build(
        confdir=tmp_path, srcdir=tmp_path / "docs", outdir=tmp_path / "_build"
    )

    assert build.doc_path is None
    assert "Edit on GitHub" not in build.index_html
