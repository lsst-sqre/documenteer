"""A package documenting the aliases it re-exports from a private module.

This mirrors ``safir.pydantic``, which publishes ``IvoaIsoDatetime`` from
``safir.pydantic._types``: an alias page's ``py:module`` context is the
package the alias is documented *from*, never the module it was written
in, which is the module the fragment index has to be keyed by.
"""

from __future__ import annotations

from ._types import IsoDatetime, TrimmedName, register

__all__ = ["IsoDatetime", "TrimmedName", "register"]
