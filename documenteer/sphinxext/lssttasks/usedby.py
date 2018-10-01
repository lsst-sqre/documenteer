"""Directive that describes what tasks use a given task, configurable, or
standalone config.
"""

from docutils.parsers.rst import Directive
from sphinx.errors import SphinxError


class UsedByTaskDirective(Directive):
    """Directive that lists the tasks that use a given task, configurable,
    or standalone config.
    """

    name = 'lsst-used-by-tasks'
    """Name of the directive in reStructuredText (`str`).
    """

    required_arguments = 0

    def run(self):
        """Main entrypoint method.

        Returns
        -------
        new_nodes : `list`
            Nodes to add to the doctree.
        """
        self._env = self.state.document.settings.env

        try:
            class_name = self.arguments[0]
        except IndexError:
            raise SphinxError(
                '{0} directive requires a class name as an '
                'argument'.format(self.directive_name)
            )
        self._logger.debug('%s using class %s',
                           self.name, class_name)
