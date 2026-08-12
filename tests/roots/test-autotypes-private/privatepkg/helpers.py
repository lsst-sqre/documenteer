"""A public module of the package that the documentation does not cover.

A reference to the class defined here resolves to a real project-local
object under a wholly public module path: the "should be exported and
documented but isn't" case that has to keep warning, and the reason the
private-path degrade gates on an underscore-prefixed path segment rather
than on project locality alone.
"""

from __future__ import annotations


class PublicUndocumented:
    """A class in a public module path that nothing documents."""
