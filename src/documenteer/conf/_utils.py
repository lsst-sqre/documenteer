"""Utilities for the Sphinx configuration modules."""

from __future__ import annotations

from pathlib import Path

from git import Repo
from sphinx.errors import ConfigError

__all__ = [
    "get_asset_path",
    "extend_static_paths_with_asset_extension",
    "get_template_dir",
    "GitRepository",
]


def _get_assert_dir() -> Path:
    """Get the absolute path to the Documenteer assets directory."""
    return Path(__file__).parent.joinpath("../assets")


def get_asset_path(name: str) -> str:
    """Get the absolute path for a static asset contained in Documenteer's
    assets directory, for use with Sphinx's ``html_static_path``.

    Parameters
    ----------
    name : `str`
        The name of a path or directory in Documenteer's assets.

    Returns
    -------
    absolute_path : `str`
        An absolute path to the file or directory that can be used in
        the ``html_static_path`` Sphinx configuration list.

    Examples
    --------
    .. code-block:: py

       html_static_path: List[str] = [
           get_asset_path("rubin-titlebar-imagotype-dark.svg"),
           get_asset_path("rubin-titlebar-imagotype-light.svg"),
       ]
    """
    asset_path = _get_assert_dir().joinpath(name).resolve()
    if not asset_path.exists():
        raise ConfigError(
            f"Documenteer asset {name!r} does not exist.\n"
            f"Tried to resolve to {asset_path} inside the installed "
            "Documenteer package."
        )
    return str(asset_path)


def extend_static_paths_with_asset_extension(
    html_static_path: list[str], extension: str
) -> None:
    """Extend a Sphinx ``html_static_path`` configuration list with the
    files of a given extension in Documenteer's assets directory.
    """
    asset_dir = _get_assert_dir()
    new_paths = [str(p) for p in asset_dir.glob(f"*.{extension}")]
    html_static_path.extend(new_paths)


def get_template_dir(root: str) -> str:
    """Get the absolute path for a Documenteer template directory, for use
    with Sphinx's ``templates_path``.

    Parameters
    ----------
    root : `str`
        A root directory for the templates. For example, ``pydata`` is the root
        for templates that override the pydata theme.

    Returns
    -------
    absolute_path : `str`
        An absolute path to the templates directory, for use with the
        ``templates_path`` Sphinx configuration.

    Examples
    --------
    .. code-block:: py

       templates_path = [get_template_dir("pydata")]
    """
    dirname = Path(__file__).parent.joinpath("../templates", root)
    dirname.resolve()
    if not dirname.is_dir():
        raise ConfigError(
            f"Documenteer template directory root {root!r} does not exist.\n"
            f"Tried to resolve to {dirname} inside the installed "
            "Documenteer package."
        )
    return str(dirname)


class GitRepository:
    """Access to to metadata about the Git repository of the documentation
    project.
    """

    def __init__(self, dirname: Path) -> None:
        self._repo = Repo(dirname, search_parent_directories=True)

    @property
    def working_tree_dir(self) -> Path:
        """The root directory of the Git repository."""
        path = self._repo.working_tree_dir
        if path is None:
            raise RuntimeError("Git repository is not available.")
        return Path(path)


def extend_excludes_for_non_index_source(
    exclude_patterns: list[str],
    extension: str,
    working_dir: Path | None = None,
) -> None:
    """Extend the exclude_patterns configuration to include files with a
    specific extension that aren't the index file.

    This is useful for technotes where only the ``index{.ext}`` file is valid
    as a source file.

    Parameters
    ----------
    exclude_patterns
        The Sphinx configuration, ``exclude_patterns``. This configuration is
        modified in place.
    extension
        The file extension to exclude. Examples: ``"ipynb"``, ``"md"``,
        ``"rst"``. The extension does not include the leading period.
    working_dir
        The working directory to search for files. If not provided, the
        current working directory is used. This should be equivalent to the
        directory where the Sphinx configuration is located.
    """
    cwd = Path.cwd() if working_dir is None else working_dir

    for p in cwd.glob(f"**/*.{extension}"):
        if p.name != f"index.{extension}":
            exclude_patterns.append(str(p.relative_to(cwd)))  # noqa: PERF401
