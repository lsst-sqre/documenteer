"""Sphinx directive ``lsst-subtasks`` that documents the subtasks in a Task's
Config class.
"""

__all__ = ('SubtasksDirective',)

from docutils.parsers.rst import Directive
from sphinx.util.logging import getLogger
from sphinx.errors import SphinxError

from .taskutils import get_task_config_class, get_subtask_fields
from .formatters import format_configurablefield_nodes


class SubtasksDirective(Directive):
    """``lsst-subtasks`` directive that renders documentation for the subtasks
    associated with an ``lsst.pipe.base.Task``.

    Examples
    --------
    Use the directive like this:

    .. code-block:: rst

       .. lsst-subtasks:: lsst.pipe.tasks.processCcd.ProcessCcdTask
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
        logger = getLogger(__name__)

        try:
            task_class_name = self.arguments[0]
        except IndexError:
            raise SphinxError('lsst-subtasks directive requires a Task class '
                              'name as an argument')
        logger.debug('lsst-subtasks using Task class %s', task_class_name)

        task_config_class = get_task_config_class(task_class_name)
        subtask_fields = get_subtask_fields(task_config_class)

        all_nodes = []
        for field_name, field in subtask_fields.items():
            iid = '.'.join((task_config_class.__module__,
                            task_config_class.__name__,
                            field_name,
                            'subtask-config'))
            all_nodes.append(
                format_configurablefield_nodes(
                    field_name, field, iid, self.state
                )
            )

        return all_nodes
