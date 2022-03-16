"""Utilities for working with Doxygen tag files.
"""

__all__ = ["get_tag_entity_names"]

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional, Sequence, Union

try:
    from sphinxcontrib.doxylink import doxylink
except ImportError:
    print(
        "sphinxcontrib.doxylink is missing. Install documenteer with the "
        "pipelines extra:\n\n  pip install documenteer[pipelines]"
    )


def get_tag_entity_names(
    tag_path: Union[str, Path], kinds: Optional[Sequence[str]] = None
) -> List[str]:
    """Get the list of API names in a Doxygen tag file.

    Parameters
    ----------
    tag_path : `str` or `~pathlib.Path`
        File path of the Doxygen tag file.
    kinds : sequence of `str`, optional
        If provided, a sequence of API kinds to include in the listing.
        Doxygen types are:

        - namespace
        - struct
        - class
        - file
        - define
        - group
        - variable
        - typedef
        - enumeration
        - function

    Returns
    -------
    names : `list` of `str`
        List of API names.
    """
    doc = ET.parse(str(tag_path))
    symbol_map = doxylink.SymbolMap(doc)
    keys = []
    for key in symbol_map._mapping.keys():
        entry = symbol_map[key]
        if kinds:
            if entry.kind in kinds:
                keys.append(key)
        else:
            keys.append(key)
    keys.sort()
    return keys
