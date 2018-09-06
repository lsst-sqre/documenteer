"""Sphinx directive ``lsst-subtasks`` that documents the subtasks in a Task's
Config class.
"""

__all__ = ('SubtasksDirective',)

from docutils.parsers.rst import Directive
from sphinx.util.logging import getLogger
from sphinx.errors import SphinxError

from .taskutils import get_task_config_class, get_subtask_fields
from .formatters import get_field_formatter


class SubtasksDirective(Directive):
    """``lsst-subtasks`` directive that renders documentation for the subtasks
    associated with an ``lsst.pipe.base.Task``.

    Notes
    -----
    Subtasks come from ConfigurableField and RegistryField types of
    ``lsst.pex.config`` configuration fields.

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
            field_id = '.'.join((task_config_class.__module__,
                                 task_config_class.__name__,
                                 field_name,
                                 'subtask-config'))
            try:
                format_field_nodes = get_field_formatter(field)
            except ValueError:
                logger.debug('Skipping unknown config field type, '
                             '{0!r}'.format(field))
                continue

            all_nodes.append(
                format_field_nodes(field_name, field, field_id, self.state)
            )

        return all_nodes
