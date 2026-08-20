"""Detection of the kind of Documenteer project a Sphinx build is for.

Documenteer configures two kinds of project — user guides
(`documenteer.conf.guide`, driven by a ``documenteer.toml`` file) and
technotes (`documenteer.conf.technote`, driven by a ``technote.toml``
file) — and several Sphinx extensions are loaded by both. Those
extensions need to word their build-log messages for whichever kind of
project is actually being built, so that an author is never told to edit
a file their project does not have.

This module answers that one question and nothing else. Message text
stays with each consumer, so this helper never grows knowledge of any
particular extension's settings.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

__all__ = ["ConfigSource", "detect_config_source"]

_TECHNOTE_CONFIG_FILE = "technote.toml"
"""Name of a technote's configuration file, beside its ``conf.py``."""

_GUIDE_CONFIG_FILE = "documenteer.toml"
"""Name of a user guide's configuration file.

A guide's ``documenteer.toml`` lives in the Sphinx source directory
alongside ``conf.py``, not at the repository root, so the Sphinx
``confdir`` is a sufficient anchor for it.
"""


class ConfigSource(Enum):
    """The kind of Documenteer configuration a Sphinx project is built
    from.
    """

    GUIDE = "guide"
    """A user guide, configured through a ``documenteer.toml`` file."""

    TECHNOTE = "technote"
    """A technote, configured through a ``technote.toml`` file."""

    UNKNOWN = "unknown"
    """Neither configuration file is present, so the Sphinx configuration
    came from ``conf.py`` directly.
    """


def detect_config_source(confdir: str | Path) -> ConfigSource:
    """Determine which kind of Documenteer project a Sphinx ``confdir``
    belongs to.

    Parameters
    ----------
    confdir
        The Sphinx configuration directory: the directory holding the
        project's ``conf.py``. Both project types keep their TOML
        configuration file beside ``conf.py``, so this is a sufficient
        anchor for the check.

    Returns
    -------
    ConfigSource
        `ConfigSource.TECHNOTE` if a ``technote.toml`` sits beside
        ``conf.py``, `ConfigSource.GUIDE` if a ``documenteer.toml`` does,
        and `ConfigSource.UNKNOWN` if neither does. When both files are
        somehow present, ``technote.toml`` wins.

    Notes
    -----
    Only file names are examined, never file contents: the check is cheap
    and cannot fail on a malformed or unreadable configuration file. Any
    `OSError` raised while probing the directory (a missing or unreadable
    ``confdir``) yields `ConfigSource.UNKNOWN` — a helper whose only job
    is to word a message must never be able to fail a build.
    """
    directory = Path(confdir)
    try:
        if (directory / _TECHNOTE_CONFIG_FILE).is_file():
            return ConfigSource.TECHNOTE
        if (directory / _GUIDE_CONFIG_FILE).is_file():
            return ConfigSource.GUIDE
    except OSError:
        return ConfigSource.UNKNOWN
    return ConfigSource.UNKNOWN
