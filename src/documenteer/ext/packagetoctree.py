"""Sphinx extensions for creating toctrees for packages and modules for the
Pipelines documentation.
"""

__all__ = ["setup", "ModuleTocTree", "PackageTocTree"]

import docutils
import sphinx
from docutils.parsers.rst import Directive, directives
from sphinx.util.logging import getLogger
from sphinx.util.nodes import set_source_info

from ..version import __version__


class ModuleTocTree(Directive):
    """Toctree that automatically displays a list of modules in the Stack
    documentation.

    Notes
    -----
    Modules are detected as document paths. All modules have index pages
    with paths ``modules/{{name}}/index`` by virtue of the linking during the
    build process. Thus this directive does not directly interact with eups.

    **Options**

    ``skip``
       Module (or modules) to skip (optional). For multiple modules, provide a
       comma-delimited list. If possible, use the ``-s`` option from the
       ``stack-docs`` command-line app instead to prevent orphan document
       issues.
    """

    has_content = False

    option_spec = {"skip": directives.unchanged}

    def run(self):
        """Main entrypoint method.

        Returns
        -------
        new_nodes : `list`
            Nodes to add to the doctree.
        """
        logger = getLogger(__name__)

        env = self.state.document.settings.env
        new_nodes = []

        # Get skip list
        skipped_modules = self._parse_skip_option()

        # List of homepage documents for each module
        module_index_files = []

        # Collect paths with the form `modules/<module-name>/index`
        for docname in _filter_index_pages(env.found_docs, "modules"):
            logger.debug("module-toctree found %s", docname)
            if self._parse_module_name(docname) in skipped_modules:
                logger.debug("module-toctree skipped %s", docname)
                continue
            module_index_files.append(docname)
        module_index_files.sort()
        entries = [(None, docname) for docname in module_index_files]
        logger.debug(
            "module-toctree found %d modules", len(module_index_files)
        )

        # Add the toctree's node itself
        subnode = _build_toctree_node(
            parent=env.docname,
            entries=entries,
            includefiles=module_index_files,
            caption=None,
        )
        set_source_info(self, subnode)  # Sphinx TocTree does this.

        wrappernode = docutils.nodes.compound(
            classes=["toctree-wrapper", "module-toctree"]
        )
        wrappernode.append(subnode)
        self.add_name(wrappernode)
        new_nodes.append(wrappernode)

        return new_nodes

    def _parse_skip_option(self):
        """Parse the ``skip`` option of skipped module names."""
        try:
            skip_text = self.options["skip"]
        except KeyError:
            return []

        modules = [module.strip() for module in skip_text.split(",")]
        return modules

    def _parse_module_name(self, docname):
        """Parse the module name given a docname with the form
        ``modules/<module>/index``.
        """
        return docname.split("/")[1]


class PackageTocTree(Directive):
    """Toctree that automatically lists packages in the Stack documentation.

    Notes
    -----
    Packages are detected as document paths. All packages have index pages
    with paths ``packages/{{name}}/index`` by virtue of the linking during the
    build process. Thus this directive does not directly interact with eups.

    **Options**

    ``skip``
       Package (or packages) to skip (optional). For multiple packages, provide
       a comma-delimited list. If possible, use the ``-s`` option from the
       ``stack-docs`` command-line app instead to prevent orphan document
       issues.

    """

    has_content = False

    option_spec = {"skip": directives.unchanged}

    def run(self):
        """Main entrypoint method.

        Returns
        -------
        new_nodes : `list`
            Nodes to add to the doctree.
        """
        logger = getLogger(__name__)

        env = self.state.document.settings.env
        new_nodes = []

        # Get skip list
        skipped_packages = self._parse_skip_option()

        # List of homepage documents for each package
        package_index_files = []

        # Collect paths with the form `modules/<module-name>/index`
        for docname in _filter_index_pages(env.found_docs, "packages"):
            logger.debug("package-toctree found %s", docname)
            if self._parse_package_name(docname) in skipped_packages:
                logger.debug("package-toctree skipped %s", docname)
                continue
            package_index_files.append(docname)
        package_index_files.sort()
        entries = [(None, docname) for docname in package_index_files]
        logger.debug(
            "package-toctree found %d packages", len(package_index_files)
        )

        # Add the toctree's node itself
        subnode = _build_toctree_node(
            parent=env.docname,
            entries=entries,
            includefiles=package_index_files,
            caption=None,
        )

        set_source_info(self, subnode)  # Sphinx TocTree does this.

        wrappernode = docutils.nodes.compound(
            classes=["toctree-wrapper", "package-toctree"]
        )
        wrappernode.append(subnode)
        self.add_name(wrappernode)
        new_nodes.append(wrappernode)

        return new_nodes

    def _parse_skip_option(self):
        """Parse the ``skip`` option of skipped package names."""
        try:
            skip_text = self.options["skip"]
        except KeyError:
            return []

        packages = [package.strip() for package in skip_text.split(",")]
        return packages

    def _parse_package_name(self, docname):
        """Parse the package name given a docname with the form
        ``packages/<package>/index``.
        """
        return docname.split("/")[1]


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
        parts = docname.split("/")
        if len(parts) == 3 and parts[0] == base_dir and parts[2] == "index":
            yield docname


def _build_toctree_node(
    parent=None, entries=None, includefiles=None, caption=None
):
    """Factory for a toctree node."""
    # Add the toctree's node itself
    subnode = sphinx.addnodes.toctree()
    subnode["parent"] = parent
    subnode["entries"] = entries
    subnode["includefiles"] = includefiles
    subnode["caption"] = caption
    # These values are needed for toctree node types. We don't need/want
    # these to be configurable for module-toctree.
    subnode["maxdepth"] = 1
    subnode["hidden"] = False
    subnode["glob"] = None
    subnode["hidden"] = False
    subnode["includehidden"] = False
    subnode["numbered"] = 0
    subnode["titlesonly"] = False
    return subnode


def setup(app):
    app.add_directive("module-toctree", ModuleTocTree)
    app.add_directive("package-toctree", PackageTocTree)

    return {"version": __version__}
