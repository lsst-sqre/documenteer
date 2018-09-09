"""Directive for documenting a standalone configuration class.
"""

__all__ = ('StandaloneConfigsDirective',)

from docutils.parsers.rst import Directive
from sphinx.util.logging import getLogger
from sphinx.errors import SphinxError

from .taskutils import get_type, get_task_config_fields
from .formatters import get_field_formatter


class StandaloneConfigsDirective(Directive):
    """``lsst-config-fields`` directive that renders documentation for the
    configuration fields associated with standalone ``lsst.pex.config.Config``
    class.
    """

    directive_name = 'lsst-config-fields'
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
        logger = getLogger(__name__)

        try:
            config_class_name = self.arguments[0]
        except IndexError:
            raise SphinxError(
                '{} directive requires a Config class '
                'name as an argument'.format(self.directive_name))
        logger.debug('%s using Config class %s', self.directive_name,
                     config_class_name)

        config_class = get_type(config_class_name)

        config_fields = get_task_config_fields(config_class)

        all_nodes = []

        for field_name, field in config_fields.items():
            field_id = '.'.join((
                config_class.__module__,
                config_class.__name__,
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
