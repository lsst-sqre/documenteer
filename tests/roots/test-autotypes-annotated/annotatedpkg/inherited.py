"""A model that inherits a field whose metadata names enum members.

This module deliberately does *not* use ``from __future__ import
annotations``, so the base model's annotations are real ``Annotated``
objects. On the base model's own page Sphinx renders the field's type by
stringifying them, which mangles each enum member's ``repr()``. On the
*subclass's* page it renders the annotation's source text instead:
autodoc copies each base class's source annotations onto the class it
documents, and that string is the only annotation of the inherited field
the subclass has. The copy is a side effect of autodoc documenting the
class, so it exists only in a build that reads the sources, not in one
that resolves references out of pickled doctrees.
"""

from typing import Annotated

from extphase import ExecutionPhase
from pydantic import BaseModel, Field

__all__ = ["QueuedJob", "SerializedJob"]


class SerializedJob(BaseModel):
    """A stored job, in the shape of Safir's ``uws.SerializedJob``."""

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
    """A field whose metadata names enum members by attribute path."""


class QueuedJob(SerializedJob):
    """A job that inherits ``phase``, in the shape of Safir's ``uws.Job``.

    The model adds an annotation of its own so that it has a class-level
    ``__annotations__`` for autodoc to extend.
    """

    queue: str = "default"
    """The queue the job waits in."""
