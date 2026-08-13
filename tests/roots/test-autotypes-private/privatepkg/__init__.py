"""A package whose public API is implemented in a private module.

This is the only module the test root documents, so it is also the only
module prefix the reference ladder's project-local test knows about.
"""

from __future__ import annotations

from ._impl import Stamp

__all__ = ["Stamp"]
