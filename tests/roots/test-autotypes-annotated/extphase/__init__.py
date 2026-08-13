"""An "external" package with no intersphinx inventory.

The documented package imports :class:`ExecutionPhase` into the module
where its models are defined, but never re-exports it, so the members
written into a field's ``Annotated`` metadata are reachable from neither
the documented module's namespace nor any inventory.
"""

from __future__ import annotations

from enum import Enum

__all__ = ["ExecutionPhase"]


class ExecutionPhase(str, Enum):
    """The phase a job is in."""

    PENDING = "PENDING"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
