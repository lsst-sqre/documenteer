"""Targets and reference roles for LSST Task objects.
"""

__all__ = ('format_task_id', 'TaskTopicTargetDirective')

from docutils import nodes
from docutils.parsers.rst import Directive
from sphinx.util.logging import getLogger
from sphinx.errors import SphinxError


def format_task_id(task_class_name):
    """Format the ID of a task topic reference node.

    Parameters
    ----------
    task_class_name : `str`
        Importable name of the task class. For example,
        ``'lsst.pipe.tasks.processCcd.ProcessCcdTask'``.

    Returns
    -------
    task_id : `str`
        Node ID for the task topic reference node.
    """
    return nodes.make_id('lsst-task-{}'.format(task_class_name))


class TaskTopicTargetDirective(Directive):
    """``lsst-task`` directive that labels a Task's topic page.
    """

    directive_name = 'lsst-task'
    """Default name of this directive.
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
        env = self.state.document.settings.env
        logger = getLogger(__name__)

        try:
            task_class_name = self.arguments[0]
        except IndexError:
            raise SphinxError(
                '{} directive requires a Task class name as an '
                'argument'.format(self.directive_name)
            )
        logger.debug('%s using Task class %s',
                     self.directive_name, task_class_name)

        target_id = format_task_id(task_class_name)
        target_node = nodes.target('', '', ids=[target_id])

        # Store these task topic nodes in the environment for later cross
        # referencing.
        if not hasattr(env, 'lsst_tasks'):
            env.lsst_tasks = {}
        env.lsst_tasks[target_id] = {
            'docname': env.docname,
            'lineno': self.lineno,
            'target': target_node,
        }

        return [target_node]
