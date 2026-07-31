"""Helpers shared by the ``documenteer.ext.autotypes`` sub-extensions."""

from __future__ import annotations

from typing import Any

import sphinx

SPHINX_LT_9 = sphinx.version_info[0] < 9


def _is_annotated_alias(obj: Any) -> bool:
    """Return True for assignment-style ``Annotated[...]`` module aliases."""
    try:
        return not isinstance(obj, type) and hasattr(obj, "__metadata__")
    except Exception:
        return False
