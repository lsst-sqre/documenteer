"""A model whose annotations Sphinx renders from their source text.

``from __future__ import annotations`` leaves this module's annotations
as strings, and Sphinx's ``get_type_hints`` wrapper falls back to those
raw strings whenever evaluating the class's annotations raises — which it
does for a Pydantic model, because autodoc first copies each base class's
*source* annotations onto the model. Sphinx then unparses the annotation
exactly as written, enum members and all.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field

from extphase import ExecutionPhase

__all__ = ["Job"]


class Job(BaseModel):
    """A job record, in the shape of Safir's ``uws.Job``."""

    phase: Annotated[
        ExecutionPhase,
        Field(
            title="Execution phase",
            examples=[
                ExecutionPhase.PENDING,
                ExecutionPhase.EXECUTING,
                ExecutionPhase.COMPLETED,
            ],
        ),
    ] = ExecutionPhase.PENDING
    """A field whose metadata names enum members by attribute path.

    Each ``ExecutionPhase.MEMBER`` in the source annotation unparses to a
    dotted cross-reference target. The bare `ExecutionPhase` resolves
    through this model's MRO (this module's namespace imports it) and
    degrades as an external object, but the dotted member paths are names
    in no scanned namespace.
    """
