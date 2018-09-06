"""Directive for documenting a task's configuration (aside from retargetable
subtasks).
"""

__all__ = ('TaskConfigsDirective',)

from docutils.parsers.rst import Directive
from sphinx.util.logging import getLogger
from sphinx.errors import SphinxError

from .taskutils import get_task_config_class, get_task_config_fields
from .formatters import get_field_formatter


class TaskConfigsDirective(Directive):
    """``lsst-task-configs`` directive that renders documentation for the
    configuration fields associated iwth an ``lsst.pipe.base.Task``.

    Configurable subtasks are documented by the ``lsst-subtasks`` directive
    instead.
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
        from lsst.pex.config import ConfigurableField, RegistryField

        logger = getLogger(__name__)

        try:
            task_class_name = self.arguments[0]
        except IndexError:
            raise SphinxError('lsst-subtasks directive requires a Task class '
                              'name as an argument')
        logger.debug('lsst-taskconfigs using Task class %s', task_class_name)

        task_config_class = get_task_config_class(task_class_name)
        config_fields = get_task_config_fields(task_config_class)

        all_nodes = []
        for field_name, field in config_fields.items():
            # Skip fields documented via the `lsst-subtasks` directive
            if isinstance(field, (ConfigurableField, RegistryField)):
                continue

            field_id = '.'.join((
                task_config_class.__module__,
                task_config_class.__name__,
                field_name,
                'field'
            ))

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
