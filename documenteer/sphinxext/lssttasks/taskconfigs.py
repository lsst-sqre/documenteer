"""Directive for documenting a task's configuration (aside from retargetable
subtasks).
"""

__all__ = ('TaskConfigsDirective',)

from docutils import nodes
from docutils.parsers.rst import Directive
from sphinx.util.logging import getLogger
from sphinx.errors import SphinxError

from .taskutils import get_task_config_class, get_task_config_fields
from .formatters import get_field_formatter
from .crossrefs import format_configfield_id


class TaskConfigsDirective(Directive):
    """``lsst-task-config-fields`` directive that renders documentation for the
    configuration fields associated with an ``lsst.pipe.base.Task``.

    Configurable subtasks are documented by the ``lsst-task-config-subtasks``
    directive instead.
    """

    directive_name = 'lsst-task-config-fields'
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
        from lsst.pex.config import ConfigurableField, RegistryField

        logger = getLogger(__name__)

        try:
            task_class_name = self.arguments[0]
        except IndexError:
            raise SphinxError(
                '{} directive requires a Task class '
                'name as an argument'.format(self.directive_name))
        logger.debug('%s using Task class %s', task_class_name)

        task_config_class = get_task_config_class(task_class_name)
        config_fields = get_task_config_fields(task_config_class)

        all_nodes = []
        for field_name, field in config_fields.items():
            # Skip fields documented via the `lsst-task-config-subtasks`
            # directive
            if isinstance(field, (ConfigurableField, RegistryField)):
                continue

            field_id = format_configfield_id(
                '.'.join((task_config_class.__module__,
                          task_config_class.__name__)),
                field_name)

            try:
                format_field_nodes = get_field_formatter(field)
            except ValueError:
                logger.debug('Skipping unknown config field type, '
                             '{0!r}'.format(field))
                continue

            all_nodes.append(
                format_field_nodes(field_name, field, field_id, self.state,
                                   self.lineno)
            )

        # Fallback if no configuration items are present
        if len(all_nodes) == 0:
            message = 'No configuration fields.'
            return [nodes.paragraph(text=message)]

        return all_nodes
