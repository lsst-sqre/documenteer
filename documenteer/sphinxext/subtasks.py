"""Sphinx directive ``lsst-subtasks`` that documents the subtasks in a Task's
Config class.
"""

__all__ = ('setup', 'SubtasksDirective')

from docutils.parsers.rst import Directive
try:
    # Sphinx 1.6+
    from sphinx.util.logging import getLogger
except ImportError:
    getLogger = None
from sphinx.errors import SphinxError
from pkg_resources import get_distribution, DistributionNotFound


class SubtasksDirective(Directive):
    """``lsst-subtasks`` directive that renders documentation for the subtasks
    associated with an ``lsst.pipe.base.Task``.
    """

    has_content = False

    required_arguments = 1

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

        try:
            task_class_name = self.arguments[0]
        except IndexError:
            raise SphinxError('lsst-subtasks directive requires a Task class '
                              'name as an argument')
        logger.debug('lsst-subtasks using Task class %s', task_class_name)


def setup(app):
    app.add_directive('lsst-subtasks', SubtasksDirective)

    try:
        __version__ = get_distribution('documenteer').version
    except DistributionNotFound:
        # package is not installed
        __version__ = 'unknown'
    return {'version': __version__}
