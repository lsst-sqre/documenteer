"""Sphinx extension to generate a list of doxylink-based links to C++ APIs in
a namespace.
"""

__all__ = ["setup", "AutoCppApi", "filter_symbolmap"]

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Union

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util.docutils import SphinxDirective

from ..sphinxext.utils import parse_rst_content
from ..version import __version__

try:
    from sphinxcontrib.doxylink import doxylink
except ImportError:
    print(
        "sphinxcontrib.doxylink is missing. Install documenteer with the "
        "pipelines extra:\n\n  pip install documenteer[pipelines]"
    )
    raise


if TYPE_CHECKING:
    import sphinx.application
    import sphinx.config


def cache_doxylink_symbolmap(
    app: "sphinx.application.Sphinx",
    config: "sphinx.config.Config",
) -> None:
    """Cache the doxylink SymbolMap used by the AutoCppApi directive, into
    the environment.

    This is connected to the ``config-inited`` event.

    Notes
    -----
    This function caches the ``doxylink.SymbolMap`` instance into the
    environment under two levels of keys:

    1. ``"documenteer_autocppapi_symbolmaps"``
    2. The value of the ``"documenteer_autocppapi_doxylink_role"``
       configuration variable.

    If the doxygen tag file cannot be found by `load_symbolmap`, the value
    persisted to the environment is `None` rather than a symbol map.
    """
    doxylink_role: str = config["documenteer_autocppapi_doxylink_role"]
    try:
        symbol_map: Union[doxylink.SymbolMap, None] = load_symbolmap(
            doxylink_role, config
        )
    except SymbolMapLoadError:
        symbol_map = None

    key = "documenteer_autocppapi_symbolmaps"
    if key in config:
        if isinstance(config[key], dict):
            config[key][doxylink_role] = symbol_map
    else:
        config[key] = {doxylink_role: symbol_map}


def load_symbolmap(
    doxylink_role: str, config: "sphinx.config.Config"
) -> doxylink.SymbolMap:
    """Load the doxylink SymbolMap given Sphinx configuration.

    Raises
    ------
    SymbolMapLoadError
        Raised if the symbol map for ``doxylink_role`` cannot be loaded either
        because the file does not exist or the doxylink configuration does not
        exist.
    """
    if doxylink_role in config["doxylink"]:
        if isinstance(config["doxylink"], dict):
            if isinstance(config["doxylink"][doxylink_role], tuple):
                tag_path = Path(config["doxylink"][doxylink_role][0])
                if not tag_path.exists():
                    raise SymbolMapLoadError(
                        "Could not load tag file for Doxylink "
                        f"{doxylink_role} role."
                    )
                doc = ET.parse(str(tag_path))
                return doxylink.SymbolMap(doc)
    raise SymbolMapLoadError(
        f"Could not load tag file for Doxylink {doxylink_role} role."
    )


class SymbolMapLoadError(RuntimeError):
    """Exception related to loading a Doxylink SymbolMap."""


def filter_symbolmap(
    symbol_map: doxylink.SymbolMap,
    kinds: Optional[Set[str]] = None,
    match: Optional[str] = None,
) -> List[str]:
    """Filter the entries in a symbol map to only those that match a certain
    API type or name regular expression.

    Parameters
    ----------
    symbol_map : ``doxylink.SymbolMap``
        The Doxylink SymbolMap.
    kinds : `set` of `str`, optional
        The kinds of APIs to filter for. The class-like APIs are:

        - ``class``
        - ``struct``
        - ``union``
        - ``interface``
    match : `str`
        A string that can be compiled into a regular expression. This regular
        expression matches APIs

    Returns
    -------
    names : `list` of `str`
        The names of APIs that match the criteria.
    """
    names: List[str] = []
    pattern: Optional[Any]
    if match:
        pattern = re.compile(match)
    else:
        pattern = None
    for key in symbol_map._mapping.keys():
        entry = symbol_map[key]
        if kinds:
            if entry.kind in kinds:
                if pattern:
                    if pattern.search(key):
                        names.append(key)
                else:
                    names.append(key)
        else:
            names.append(key)
    names.sort()
    return names


class AutoCppApi(SphinxDirective):
    """The ``autocppapi`` directive that lists C++ APIs within a namespace,
    as detected by doxylink.
    """

    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    has_content = False
    option_spec = {
        "doxylink-role": directives.unchanged,
    }

    def run(self) -> List[nodes.Node]:
        """Execute the directive."""
        if "doxylink-role" in self.options:
            doxylink_role = self.options["doxylink-role"]
        else:
            doxylink_role = self.env.config[
                "documenteer_autocppapi_doxylink_role"
            ]

        try:
            key = "documenteer_autocppapi_symbolmaps"
            symbol_map: Union[doxylink.SymbolMap, None] = self.env.config[key][
                doxylink_role
            ]
        except KeyError:
            symbol_map = load_symbolmap(doxylink_role, self.env.config)

        namespace_prefix = self.arguments[0]

        node_list: List[nodes.Node] = []

        if symbol_map is not None:
            node_list.extend(
                self._make_namespace_section(
                    prefix=namespace_prefix,
                    heading=namespace_prefix,
                    symbol_map=symbol_map,
                    doxylink_role=doxylink_role,
                )
            )
        else:
            node_list.extend(
                self._make_fallback_section(
                    prefix=namespace_prefix, heading=namespace_prefix
                )
            )

        return node_list

    def _make_namespace_section(
        self,
        *,
        prefix: str,
        heading: str,
        symbol_map: doxylink.SymbolMap,
        doxylink_role: str,
        kinds: Optional[Set[str]] = None,
    ) -> List[nodes.Node]:
        """Create nodes for a section that lists links to APIs under a single
        C++ namespace (prefix).

        Parameters
        ----------
        prefix : `str`
            The API refix to match to symbols. E.g. ``lsst::afw::table``.
        heading : `str`
            The heading to use for the section. Normally this is the name
            of the namespace, which might be the same as ``prefix``.
        symbol_map : ``doxylink.SymbolMap``
            The symbol map.
        kinds : `set` of `str`, optional
            The kinds of APIs to list. By default, this is the set:

            - class
            - struct
            - union
            - interface

        Returns
        -------
        nodes : `list` of ``docutils.nodes.Node``
            A list of nodes. The node list is a single item, which is a
            "section" node that wraps all other nodes.
        """
        _kinds: Set[str]
        if kinds is None:
            # Default API kinds: these are all "class-like"
            _kinds = {"class", "struct", "union", "interface"}
        else:
            _kinds = kinds
        names = filter_symbolmap(symbol_map, kinds=_kinds, match=prefix)

        node_list: List[nodes.Node] = []
        if names:
            node_list.append(nodes.title(text=heading))
        else:
            return node_list

        rst_text = ["\n"]
        for name in names:
            escaped_name = name.replace("<", r"\<").replace(">", r"\>")
            rst_text.append(f"- :{doxylink_role}:`{escaped_name}`")
        node_list.extend(parse_rst_content("\n".join(rst_text), self.state))

        section = nodes.section()
        section_id = nodes.make_id(f"cppapi-{prefix}")
        section["ids"].append(section_id)
        section["names"].append(section_id)
        section.extend(node_list)

        return [section]

    def _make_fallback_section(
        self, *, prefix: str, heading: str
    ) -> List[nodes.Node]:
        """Create a section node in the case that a symbol map could not be
        loaded;
        """
        node_list: List[nodes.Node] = []

        node_list.append(nodes.title(text=heading))

        node_list.append(
            nodes.paragraph(
                text="This section is empty because the Doxygen tag file is "
                "not available."
            )
        )

        section = nodes.section()
        section_id = nodes.make_id(f"cppapi-{prefix}")
        section["ids"].append(section_id)
        section["names"].append(section_id)
        section.extend(node_list)
        return [section]


def setup(app: "sphinx.application.Sphinx") -> Dict[str, Any]:
    """Set up the ``documenteer.ext.autocppapi`` Sphinx extensions."""
    # Configuration values
    app.add_config_value("documenteer_autocppapi_doxylink_role", "", "html")

    # Events
    app.connect("config-inited", cache_doxylink_symbolmap)

    # Directives
    app.add_directive("autocppapi", AutoCppApi)

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
