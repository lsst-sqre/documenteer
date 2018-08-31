"""Sphinx directive ``lsst-subtasks`` that documents the subtasks in a Task's
Config class.
"""

__all__ = ('setup', 'SubtasksDirective')

from importlib import import_module
import inspect

from docutils import nodes
from docutils.statemachine import ViewList
from docutils.parsers.rst import Directive
try:
    # Sphinx 1.6+
    from sphinx.util.logging import getLogger
except ImportError:
    getLogger = None
from sphinx.errors import SphinxError
from sphinx.util.docutils import switch_source_input
from pkg_resources import get_distribution, DistributionNotFound


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
        type_item_content += self._make_python_xref_nodes(
            field_type,
            hide_namespace=True)
        type_item.append(type_item_content)
        dl.append(type_item)

        # Default of this field
        default_item = nodes.definition_list_item()
        default_item.append(nodes.term(text="Default"))
        target_type = '.'.join((field.target.__module__,
                                field.target.__name__))
        default_item_content = nodes.definition()
        default_item_content += self._make_python_xref_nodes(target_type)
        default_item.append(default_item_content)
        dl.append(default_item)

        # Doc for this ConfigurableField, parsed as rst
        doc_container_node = nodes.container()
        doc_container_node += self._parse_rst_content(field.doc)

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

    def _make_python_xref_nodes(self, py_obj, hide_namespace=False):
        """Make docutils nodes containing a cross-reference to a Python
        object

        Parameters
        ----------
        py_obj : `str`
            Name of the Python object. For example
            `mypackage.mymodule.MyClass`.
        hide_namespace : `bool`, optional
            If `True`, the namespace of the object is hidden in the rendered
            cross reference. Internally, this uses ``:py:obj:`~{py_obj}` (note
            tilde).

        Returns
        -------
        instance from ``docutils.nodes``
            Docutils node representing the cross reference.
        """
        if hide_namespace:
            template = ':py:obj:`~{}`\n'
        else:
            template = ':py:obj:`{}`\n'
        xref_text = template.format(py_obj)

        return self._parse_rst_content(xref_text)

    def _parse_rst_content(self, content):
        """Parse rST-formatted string content into docutils nodes

        Parameters
        ----------
        content : `str`
            ReStructuredText-formatted content

        Returns
        -------
        instance from ``docutils.nodes``
            Docutils node representing the ``content``.
        """
        # http://www.sphinx-doc.org/en/master/extdev/markupapi.html
        # #parsing-directive-content-as-rest
        container_node = nodes.section()
        container_node.document = self.state.document

        viewlist = ViewList()
        for i, line in enumerate(content.splitlines()):
            viewlist.append(line, source='', offset=i)

        with switch_source_input(self.state, viewlist):
            self.state.nested_parse(viewlist, 0, container_node)

        return container_node.children


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


def setup(app):
    app.add_directive('lsst-subtasks', SubtasksDirective)

    try:
        __version__ = get_distribution('documenteer').version
    except DistributionNotFound:
        # package is not installed
        __version__ = 'unknown'
    return {'version': __version__}
