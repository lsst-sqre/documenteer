"""Sphinx extensions for creating toctrees for packages and modules for the
Pipelines documentation.
"""

__all__ = ('setup', 'ModuleTocTree', 'PackageTocTree')

import docutils
from docutils.parsers.rst import Directive
import sphinx
try:
    # Sphinx 1.6+
    from sphinx.util.logging import getLogger
except ImportError:
    getLogger = None
from sphinx.util.nodes import set_source_info

from .._version import get_versions
__version__ = get_versions()['version']
del get_versions


class ModuleTocTree(Directive):
    """Toctree that automatically displays a list of modules in the Stack
    documentation.

    Modules are detected as document paths. All modules have index pages
    with paths ``modules/{{name}}/index`` by virtue of the linking during the
    build process. Thus this directive does not directly interact with eups.
    """

    has_content = False

    def run(self):
        """Main entrypoint method.

        Returns
        -------
        new_nodes : `list`
            Nodes to add to the doctree.
        """
        if getLogger is not None:
            # Sphinx 1.6+
            logger = getLogger(__name__)
        else:
            # Previously Sphinx's app was also the logger
            logger = self.state.document.settings.env.app

        env = self.state.document.settings.env
        new_nodes = []

        # List of homepage documents for each module
        module_index_files = []
        entries = []

        # Collect paths with the form `modules/<module-name>/index`
        for docname in _filter_index_pages(env.found_docs, 'modules'):
            module_index_files.append(docname)
            entries.append((None, docname))
            logger.debug('module-toctree found %s', docname)
        logger.debug('module-toctree found %d modules',
                     len(module_index_files))

        # Add the toctree's node itself
        subnode = _build_toctree_node(
            parent=env.docname,
            entries=entries,
            includefiles=module_index_files,
            caption=None)
        set_source_info(self, subnode)  # Sphinx TocTree does this.

        wrappernode = docutils.nodes.compound(classes=['toctree-wrapper',
                                                       'module-toctree'])
        wrappernode.append(subnode)
        self.add_name(wrappernode)
        new_nodes.append(wrappernode)

        return new_nodes


class PackageTocTree(Directive):
    """Toctree that automatically lists packages in the Stack documentation.

    Packages are detected as document paths. All packages have index pages
    with paths ``packages/{{name}}/index`` by virtue of the linking during the
    build process. Thus this directive does not directly interact with eups.
    """

    has_content = False

    def run(self):
        """Main entrypoint method.

        Returns
        -------
        new_nodes : `list`
            Nodes to add to the doctree.
        """
        if getLogger is not None:
            # Sphinx 1.6+
            logger = getLogger(__name__)
        else:
            # Previously Sphinx's app was also the logger
            logger = self.state.document.settings.env.app

        env = self.state.document.settings.env
        new_nodes = []

        # List of homepage documents for each package
        package_index_files = []
        entries = []

        # Collect paths with the form `modules/<module-name>/index`
        for docname in _filter_index_pages(env.found_docs, 'packages'):
            package_index_files.append(docname)
            entries.append((None, docname))
            logger.debug('package-toctree found %s', docname)
        logger.debug('package-toctree found %d packages',
                     len(package_index_files))

        # Add the toctree's node itself
        subnode = _build_toctree_node(
            parent=env.docname,
            entries=entries,
            includefiles=package_index_files,
            caption=None)

        set_source_info(self, subnode)  # Sphinx TocTree does this.

        wrappernode = docutils.nodes.compound(classes=['toctree-wrapper',
                                                       'package-toctree'])
        wrappernode.append(subnode)
        self.add_name(wrappernode)
        new_nodes.append(wrappernode)

        return new_nodes


def _filter_index_pages(docnames, base_dir):
    """Filter docnames to only yield paths of the form
    ``<base_dir>/<name>/index``

    Parameters
    ----------
    docnames : `list` of `str`
        List of document names (``env.found_docs``).
    base_dir : `str`
        Base directory of all sub-directories containing index pages.

    Yields
    ------
    docname : `str`
        Document name that meets the pattern.
    """
    for docname in docnames:
        parts = docname.split('/')
        if len(parts) == 3 and parts[0] == base_dir and parts[2] == 'index':
            yield docname


def _build_toctree_node(parent=None, entries=None, includefiles=None,
                        caption=None):
    """Factory for a toctree node.
    """
    # Add the toctree's node itself
    subnode = sphinx.addnodes.toctree()
    subnode['parent'] = parent
    subnode['entries'] = entries
    subnode['includefiles'] = includefiles
    subnode['caption'] = caption
    # These values are needed for toctree node types. We don't need/want
    # these to be configurable for module-toctree.
    subnode['maxdepth'] = 1
    subnode['hidden'] = False
    subnode['glob'] = None
    subnode['hidden'] = False
    subnode['includehidden'] = False
    subnode['numbered'] = 0
    subnode['titlesonly'] = False
    return subnode


def setup(app):
    app.add_directive('module-toctree', ModuleTocTree)
    app.add_directive('package-toctree', PackageTocTree)
    return {'version': __version__}
