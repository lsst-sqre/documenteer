"""Sphinx extension to generate a list of doxylink-based links to C++ APIs in
a namespace.
"""

__all__ = ['setup', 'AutoCppApi']

import re
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Sequence, Optional, Any
import xml.etree.ElementTree as ET

from docutils.nodes import Node
from docutils.parsers.rst import directives
from pkg_resources import get_distribution
from sphinx.util.docutils import SphinxDirective

try:
    from sphinxcontrib.doxylink import doxylink
except ImportError:
    print(
        'sphinxcontrib.doxylink is missing. Install documenteer with the '
        'pipelines extra:\n\n  pip install documenteer[pipelines]'
    )
    raise


if TYPE_CHECKING:
    import sphinx.application
    import sphinx.config


def cache_doxylink_symbolmap(
        app: 'sphinx.application.Sphinx',
        config: 'sphinx.config.Config',
        ) -> None:
    """Cache the doxylink SymbolMap used by the AutoCppApi directive, into
    the environment.

    This is connected to the ``config-inited`` event.
    """
    doxylink_role: str = config['documenteer_autocppapi_doxylink_role']
    symbol_map = load_symbolmap(doxylink_role, config)
    key = 'documenteer_autocppapi_symbolmaps'
    if key in config:
        if isinstance(config[key], dict):
            config[key][doxylink_role] = symbol_map  # type: ignore
    else:
        config[key] = {doxylink_role: symbol_map}


def load_symbolmap(
    doxylink_role: str,
    config: 'sphinx.config.Config'
) -> doxylink.SymbolMap:
    """Load the doxylink SymbolMap given Sphinx configuration.
    """
    if doxylink_role in config['doxylink']:
        if isinstance(config['doxylink'], dict):
            if isinstance(config['doxylink'][doxylink_role], tuple):
                tag_path = Path(config['doxylink'][doxylink_role][0])
                doc = ET.parse(str(tag_path))
                return doxylink.SymbolMap(doc)
    raise RuntimeError(
        f'Could not load tag file for Doxylink {doxylink_role} role')


def filter_symbolmap(
    symbol_map: doxylink.SymbolMap,
    kinds: Optional[Sequence[str]] = None,
    match: Optional[str] = None
) -> List[str]:
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
        'doxylink-role': directives.unchanged,
    }

    def run(self) -> List[Node]:
        """Execute the directive.
        """
        if 'doxylink-role' in self.options:
            doxylink_role = self.options['doxylink-role']
        else:
            doxylink_role = self.env.config[
                'documenteer_autocppapi_doxylink_role']

        try:
            key = 'documenteer_autocppapi_symbolmaps'
            symbol_map: doxylink.SymbolMap \
                = self.env.config[key][doxylink_role]
        except KeyError:
            symbol_map = load_symbolmap(doxylink_role, self.env.config)

        namespace_prefix = self.arguments[0]

        class_entities = filter_symbolmap(
            symbol_map, kinds=['class'], match=namespace_prefix)
        print(class_entities)

        return []


def setup(app: "sphinx.application.Sphinx") -> Dict[str, Any]:
    """Set up the ``documenteer.ext.autocppapi`` Sphinx extensions.
    """
    # Configuration values
    app.add_config_value(
        'documenteer_autocppapi_doxylink_role', '', 'html')

    # Events
    app.connect('config-inited', cache_doxylink_symbolmap)

    # Directives
    app.add_directive('autocppapi', AutoCppApi)

    return {
        'version': get_distribution('documenteer').version,
        'parallel_read_safe': True,
        'parallel_write_safe': True
    }
