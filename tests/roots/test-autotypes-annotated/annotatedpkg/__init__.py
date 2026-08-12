"""A package that documents models it re-exports from other modules.

Documenting a model from the package it is re-exported from — rather than
from the module that defines it — is what puts the names in its
``Annotated`` metadata out of the documented module's reach, which is the
situation this test root is about.
"""

from __future__ import annotations

from .constrained import KafkaSettings, SentryConfig
from .phased import Job

__all__ = ["Job", "KafkaSettings", "SentryConfig"]
