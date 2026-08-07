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
import re
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import git
import pytest
from git import Actor, Repo
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

# A documenteer.toml driving the real user-guide preset, whose github_url and
# default github_default_branch ("main") produce DP2_INDEX_URL.
GUIDE_TOML = """\
[project]
title = "Guide Preset Edit Link Test"
base_url = "https://example.lsst.io"
github_url = "https://github.com/lsst/dp2_lsst_io"
"""

GUIDE_CONF_PY = "from documenteer.conf.guide import *\n"

ACTOR = Actor("Test Author", "test@example.com")


# Constructing several ``Sphinx`` applications in one process re-runs the
# setup() of Sphinx's own built-in extensions, which warns about every node,
# directive, and role it re-registers. The pattern is anchored on that
# re-setup of a ``sphinx.*`` extension, so it can only ever match this
# artifact -- a warning from the build under test, or from Documenteer's own
# extensions, still reaches the assertions.
_REREGISTRATION_WARNING = re.compile(
    r"while setting up extension sphinx\.[\w.]+:.*is already registered"
)


def _project_warnings(warning_output: str) -> list[str]:
    """Filter a build's warning stream down to warnings about the project.

    Drops the cross-application re-registration noise described on
    `_REREGISTRATION_WARNING`, which is an artifact of the test process rather
    than of the build under test.
    """
    return [
        line
        for line in warning_output.splitlines()
        if line.strip() and not _REREGISTRATION_WARNING.search(line)
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


def test_srcdir_outside_working_tree(tmp_path: Path) -> None:
    """A repo whose working tree excludes the srcdir warns and disables.

    This shouldn't be reachable in a normal checkout -- both paths are
    resolved before they're compared -- so unlike the plain non-Git case it is
    treated as a genuine misconfiguration and does warn.
    """
    _write_project(confdir=tmp_path, srcdir=tmp_path / "docs")

    mock_repo = MagicMock()
    mock_repo.compute_relative_path.return_value = None
    mock_repo.working_tree_dir = Path("/somewhere/else")

    with patch(
        "documenteer.ext.githubeditlink.GitRepository", return_value=mock_repo
    ):
        build = _build(
            confdir=tmp_path,
            srcdir=tmp_path / "docs",
            outdir=tmp_path / "_build",
        )

    assert build.use_edit_page_button is False
    assert build.doc_path is None
    assert "Edit on GitHub" not in build.index_html
    assert len(build.warnings) == 1
    assert "could not determine the path" in build.warnings[0]


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


def test_guide_preset_dp2_layout(tmp_path: Path) -> None:
    """The real user-guide preset produces a correct edit link, dp2-style.

    This is the wiring test: it drives ``documenteer.conf.guide`` itself, so it
    fails if the extension is dropped from the preset's extensions list or if
    ``set_edit_on_github`` stops enabling the button -- neither of which the
    hand-written ``conf.py`` cases above would notice.

    The sources are committed because the guide preset auto-loads
    sphinx-last-updated-by-git (through sphinx-sitemap), which deletes
    ``sourcename`` from the context for files Git doesn't track. The edit link
    (rendered by the preset's rubin-improve-this-page box below the prev/next
    links, which mirrors pydata's edit-this-page gate) is conditioned on that
    value,
    so an *uncommitted* page renders no link no matter what ``doc_path`` says.
    """
    repo = Repo.init(tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    paths = [
        tmp_path / "documenteer.toml",
        tmp_path / "conf.py",
        docs / "index.rst",
    ]
    paths[0].write_text(GUIDE_TOML)
    paths[1].write_text(GUIDE_CONF_PY)
    paths[2].write_text(INDEX_RST)
    repo.index.add([str(p) for p in paths])
    repo.index.commit("Add docs", author=ACTOR, committer=ACTOR)

    build = _build(confdir=tmp_path, srcdir=docs, outdir=tmp_path / "_build")

    assert build.doc_path == "docs"
    assert f'href="{DP2_INDEX_URL}"' in build.index_html


def test_configured_doc_path_wins(tmp_path: Path) -> None:
    """An explicitly-configured ``doc_path`` overrides auto-detection.

    The handler runs after ``conf.py``, so without this the setting would be
    impossible to override.
    """
    Repo.init(tmp_path)
    _write_project(confdir=tmp_path, srcdir=tmp_path / "docs")
    (tmp_path / "conf.py").write_text(
        CONF_PY.replace(
            '"github_version": "main",',
            '"github_version": "main",\n    "doc_path": "custom/path",',
        )
    )

    build = _build(
        confdir=tmp_path, srcdir=tmp_path / "docs", outdir=tmp_path / "_build"
    )

    # "docs" is what auto-detection would have produced.
    assert build.doc_path == "custom/path"
    assert (
        'href="https://github.com/lsst/dp2_lsst_io/edit/main/custom/path/index.rst"'
        in build.index_html
    )


def test_configured_doc_path_survives_without_git(tmp_path: Path) -> None:
    """A configured ``doc_path`` keeps the button outside a Git checkout.

    Auto-detection is what needs a working tree; an author who supplied the
    path has already answered the question Git would have.
    """
    _write_project(confdir=tmp_path, srcdir=tmp_path / "docs")
    (tmp_path / "conf.py").write_text(
        CONF_PY.replace(
            '"github_version": "main",',
            '"github_version": "main",\n    "doc_path": "custom/path",',
        )
    )

    with patch(
        "documenteer.ext.githubeditlink.GitRepository",
        side_effect=git.InvalidGitRepositoryError,
    ) as mock_repo:
        build = _build(
            confdir=tmp_path,
            srcdir=tmp_path / "docs",
            outdir=tmp_path / "_build",
        )

    # Git is never consulted at all when the path is already known.
    mock_repo.assert_not_called()
    assert build.doc_path == "custom/path"
    assert build.use_edit_page_button is True
    assert "Edit on GitHub" in build.index_html


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
