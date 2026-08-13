"""Private implementation module for the private-path test package."""

from __future__ import annotations


class Stamp:
    """A class re-exported into the package's public namespace."""


class PrivateOnly:
    """A class the package never re-exports.

    It imports cleanly, so the reference ladder resolves it to a real
    object, but it is reachable only under this private module path — the
    documented package's namespace has no such name — so no public
    documentation target for it can ever exist.
    """
