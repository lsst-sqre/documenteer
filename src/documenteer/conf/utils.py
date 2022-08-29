"""Utilities for the Sphinx configuration modules."""

from __future__ import annotations

from pathlib import Path

from sphinx.errors import ConfigError

__all__ = ["get_asset_path"]


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
    asset_path = Path(__file__).parent.joinpath("../assets", name)
    asset_path.resolve()
    if not asset_path.exists():
        raise ConfigError(
            f"Documenteer asset {name!r} does not exist.\n"
            f"Tried to resolve to {asset_path} inside the installed "
            "Documenteer package."
        )
    return str(asset_path)
