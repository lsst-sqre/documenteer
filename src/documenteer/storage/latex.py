"""Utilities for handling LaTeX text content."""

from __future__ import annotations

import re

from pylatexenc.latex2text import LatexNodes2Text

__all__ = ["Latex"]


class Latex:
    """A class for handling LaTeX text content."""

    def __init__(self, tex: str) -> None:
        self.tex = tex

    def to_text(self) -> str:
        """Convert LaTeX to text."""
        text = LatexNodes2Text().latex_to_text(self.tex.strip())
        # Remove running spaces inside the content
        return re.sub(" +", " ", text)
