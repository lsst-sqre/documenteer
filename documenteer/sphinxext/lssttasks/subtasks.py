"""Sphinx directive ``lsst-subtasks`` that documents the subtasks in a Task's
Config class.
"""

__all__ = ('SubtasksDirective',)

from importlib import import_module
import inspect

from docutils import nodes
from docutils.parsers.rst import Directive
from sphinx.util.logging import getLogger
from sphinx.errors import SphinxError

from ..utils import parse_rst_content, make_python_xref_nodes


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
            nodes = self._make_nodes_for_configurablefield(field_name, field,
                                                           iid)
            all_nodes.append(nodes)

        return all_nodes

    def _make_nodes_for_configurablefield(self, field_name, field, section_id):
        """Create a section node that documents each ConfigurableField config
        field.

        Parameters
        ----------
        field_name : `str`
            Name of the configuration field (the attribute name of on the
            config class).
        field : ``lsst.pex.config.Field``
            A configuration field.
        section_id : `str`
            Unique identifier for this field. This is used as the id and name
            of the section node.

        Returns
        -------
        ``docutils.nodes.section``
            Section containing documentation nodes for the ConfigurableField.
        """
        # Title is the field's attribute name
        title = nodes.title(text=field_name)

        dl = nodes.definition_list()

        # Type of this configuration field
        type_item = nodes.definition_list_item()
        type_item.append(nodes.term(text="Field type"))
        field_type = '.'.join((type(field).__module__, type(field).__name__))
        type_item_content = nodes.definition()
        type_item_content += make_python_xref_nodes(
            field_type,
            self.state,
            hide_namespace=True)
        type_item.append(type_item_content)
        dl.append(type_item)

        # Default of this field
        default_item = nodes.definition_list_item()
        default_item.append(nodes.term(text="Default"))
        target_type = '.'.join((field.target.__module__,
                                field.target.__name__))
        default_item_content = nodes.definition()
        default_item_content += make_python_xref_nodes(target_type, self.state)
        default_item.append(default_item_content)
        dl.append(default_item)

        # Doc for this ConfigurableField, parsed as rst
        doc_container_node = nodes.container()
        doc_container_node += parse_rst_content(field.doc, self.state)

        # Augment documentation paragraph if the field is optional
        if field.optional:
            optional_para = nodes.paragraph(text="Optional.")
            doc_container_node.append(optional_para)

        # Package all the nodes into a `section`
        section = nodes.section()
        section['ids'].append(nodes.make_id(section_id))
        section['names'].append(section_id)
        section.append(title)
        section.append(dl)
        section.append(doc_container_node)

        return section


def get_task_config_class(task_name):
    """Get the Config class for a task given its fully-qualified name.

    Parameters
    ----------
    task_name : `str`
        Name of the task, such as ``lsst.pipe.tasks.processCcd.ProcessCcdTask`.

    Returns
    -------
    config_class : ``lsst.pipe.base.Config``\ -type
        The configuration class (not an instance) corresponding to the task.
    """
    parts = task_name.split('.')
    if len(parts) < 2:
        raise SphinxError(
            'The Task class must be fully-qualified, '
            'of the form ``module.TaskName``. Got: {}'.format(task_name)
        )
    module_name = ".".join(parts[0:-1])
    task_class_name = parts[-1]
    task_class = getattr(import_module(module_name), task_class_name)

    return task_class.ConfigClass


def get_subtask_fields(config_class):
    """Get all configurable subtask fields from a Config class.

    Parameters
    ----------
    config_class : ``lsst.pipe.base.Config``\ -type
        The configuration class (not an instance) corresponding to a Task.

    Returns
    -------
    subtask_fields : `dict`
        Mapping where keys are the config attribute names and values are
        subclasses of ``lsst.pex.config.Field`` (or specifically
        ``ConfigurableField``).
    """
    from lsst.pex.config import ConfigurableField

    def is_subtask_field(obj):
        return isinstance(obj, ConfigurableField)

    return dict(inspect.getmembers(config_class, is_subtask_field))
