"""Sphinx extension to generate a list of doxylink-based links to C++ APIs in
a namespace.
"""

__all__ = ['setup', 'AutoCppApi']

import re
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Sequence, Optional, Any
import xml.etree.ElementTree as ET

from docutils import nodes
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

from documenteer.sphinxext.utils import parse_rst_content


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

    def run(self) -> List[nodes.Node]:
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

        node_list: List[nodes.Node] = []

        # Map of doxylink.SymbolMap API types with headers.
        # There are additional types (such as `function`, `typedef`, and
        # `enumerations`), but these are generally scoped in classes already.
        api_kinds = [
            ('class', 'Classes'),
            ('struct', 'Structs'),
            ('variable', 'Variables'),
            ('define', 'Defines'),
        ]
        for kind, heading in api_kinds:
            node_list.extend(
                self._make_signature_section(
                    kind, namespace_prefix, heading, symbol_map,
                    doxylink_role))

        return node_list

    def _make_signature_section(
        self,
        kind: str,
        prefix: str,
        heading: str,
        symbol_map: doxylink.SymbolMap,
        doxylink_role: str
    ) -> List[nodes.Node]:
        names = filter_symbolmap(
            symbol_map, kinds=[kind], match=prefix)

        node_list: List[nodes.Node] = []
        if names:
            node_list.append(nodes.title(text=heading))
        else:
            return node_list

        rst_text = ['\n']
        for name in names:
            escaped_name = name.replace('<', r'\<').replace('>', r'\>')
            rst_text.append(f'- :{doxylink_role}:`{escaped_name}`')
        node_list.extend(parse_rst_content('\n'.join(rst_text), self.state))

        section = nodes.section()
        section_id = nodes.make_id(f'{prefix}-{heading}')
        section['ids'].append(section_id)
        section['names'].append(section_id)
        section.extend(node_list)

        return [section]


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
