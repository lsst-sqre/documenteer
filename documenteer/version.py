"""Version information about documenteer."""

__all__ = ["__version__", "version_info"]

import sys

if sys.version_info < (3, 8):
    from importlib_metadata import PackageNotFoundError, version
else:
    from importlib.metadata import PackageNotFoundError, version


__version__: str
"""The version string of Documenteer (PEP 440 / SemVer compatible)."""

try:
    __version__ = version("documenteer")
except PackageNotFoundError:
    # package is not installed
    __version__ = "0.0.0"

version_info = __version__.split(".")
"""The decomposed version, split across "``.``."
Use this for version comparison.
"""
