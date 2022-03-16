"""Directives that list configuration fields asssociated with tasks or
config objects.
"""

__all__ = (
    "ConfigFieldListingDirective",
    "SubtaskListingDirective",
    "StandaloneConfigFieldsDirective",
)

import functools
from typing import Any, Callable, Dict

from docutils import nodes
from docutils.parsers.rst import Directive
from sphinx.errors import SphinxError
from sphinx.util.logging import getLogger

from ..utils import (
    make_python_xref_nodes_for_type,
    make_section,
    parse_rst_content,
)
from .crossrefs import (
    format_configfield_id,
    pending_config_xref,
    pending_task_xref,
)
from .taskutils import (
    get_subtask_fields,
    get_task_config_class,
    get_task_config_fields,
    get_type,
    typestring,
)

# FIXME import typing of the lsst.pex.config.Field and
# docutils.statemachine.State parameters.
FIELD_FORMATTERS: Dict[str, Callable[[str, Any, str, Any, int], Any]] = {}
"""Internal mapping of field type strings to formatter functions.

External users should access this through `get_field_formatter`.
"""


class ConfigFieldListingDirective(Directive):
    """``lsst-task-config-fields`` directive that renders documentation for
    the configuration fields associated with an ``lsst.pipe.base.Task``.

    Configurable subtasks are documented by the ``lsst-task-config-subtasks``
    directive instead.
    """

    directive_name = "lsst-task-config-fields"
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
                "{} directive requires a Task class "
                "name as an argument".format(self.directive_name)
            )
        logger.debug("%s using Task class %s", task_class_name)

        task_config_class = get_task_config_class(task_class_name)
        config_fields = get_task_config_fields(task_config_class)

        all_nodes = []
        for field_name, field in config_fields.items():
            # Skip fields documented via the `lsst-task-config-subtasks`
            # directive
            if isinstance(field, (ConfigurableField, RegistryField)):
                continue

            field_id = format_configfield_id(
                ".".join(
                    (task_config_class.__module__, task_config_class.__name__)
                ),
                field_name,
            )

            try:
                format_field_nodes = get_field_formatter(field)
            except ValueError:
                logger.debug(
                    "Skipping unknown config field type, "
                    "{0!r}".format(field)
                )
                continue

            all_nodes.append(
                format_field_nodes(
                    field_name, field, field_id, self.state, self.lineno
                )
            )

        # Fallback if no configuration items are present
        if len(all_nodes) == 0:
            message = "No configuration fields."
            return [nodes.paragraph(text=message)]

        return all_nodes


class SubtaskListingDirective(Directive):
    """``lsst-task-config-subtasks`` directive that renders documentation for
    the subtasks associated with an ``lsst.pipe.base.Task``.

    Notes
    -----
    Subtasks come from ConfigurableField and RegistryField types of
    ``lsst.pex.config`` configuration fields.

    Examples
    --------
    Use the directive like this:

    .. code-block:: rst

       .. lsst-task-config-subtasks:: lsst.pipe.tasks.processCcd.ProcessCcdTask
    """

    directive_name = "lsst-task-config-subtasks"
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
            task_class_name = self.arguments[0]
        except IndexError:
            raise SphinxError(
                "{} directive requires a Task class name as an "
                "argument".format(self.directive_name)
            )
        logger.debug(
            "%s using Task class %s", self.directive_name, task_class_name
        )

        task_config_class = get_task_config_class(task_class_name)
        subtask_fields = get_subtask_fields(task_config_class)

        all_nodes = []
        for field_name, field in subtask_fields.items():
            field_id = format_configfield_id(
                ".".join(
                    (task_config_class.__module__, task_config_class.__name__)
                ),
                field_name,
            )
            try:
                format_field_nodes = get_field_formatter(field)
            except ValueError:
                logger.debug(
                    "Skipping unknown config field type, "
                    "{0!r}".format(field)
                )
                continue

            all_nodes.append(
                format_field_nodes(
                    field_name, field, field_id, self.state, self.lineno
                )
            )

        # Fallback if no configuration items are present
        if len(all_nodes) == 0:
            message = "No subtasks."
            return [nodes.paragraph(text=message)]

        return all_nodes


class StandaloneConfigFieldsDirective(Directive):
    """``lsst-config-fields`` directive that renders documentation for the
    configuration fields associated with standalone ``lsst.pex.config.Config``
    class.
    """

    directive_name = "lsst-config-fields"
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
                "{} directive requires a Config class "
                "name as an argument".format(self.directive_name)
            )
        logger.debug(
            "%s using Config class %s", self.directive_name, config_class_name
        )

        config_class = get_type(config_class_name)

        config_fields = get_task_config_fields(config_class)

        all_nodes = []

        for field_name, field in config_fields.items():
            field_id = format_configfield_id(
                ".".join((config_class.__module__, config_class.__name__)),
                field_name,
            )

            try:
                format_field_nodes = get_field_formatter(field)
            except ValueError:
                logger.debug(
                    "Skipping unknown config field type, "
                    "{0!r}".format(field)
                )
                continue

            all_nodes.append(
                format_field_nodes(
                    field_name, field, field_id, self.state, self.lineno
                )
            )

        # Fallback if no configuration items are present
        if len(all_nodes) == 0:
            message = "No configuration fields."
            return [nodes.paragraph(text=message)]

        return all_nodes


def get_field_formatter(field):
    """Get the config docutils node formatter function for document a config
    field.

    Parameters
    ----------
    field : ``lsst.pex.config.field.Field``
        Config field.

    Returns
    -------
    formatter : callable
        A docutils node formatter corresponding to the ``field``. Formatters
        take positional arguments:

        field_name (`str`)
            Name of the configuration field (the attribute name of on the
            config class).
        field (``lsst.pex.config.Field``)
            A configuration field.
        field_id (`str`)
            Unique identifier for this field. This is used as the id and name
            of the section node. with a -section suffix
        state (``docutils.statemachine.State``)
            Usually the directive's ``state`` attribute.
        lineno (`int`)
            Usually the directive's ``lineno`` attribute.

    Raises
    ------
    ValueError
        Raised if the field type is unknown.
    """
    try:
        return FIELD_FORMATTERS[typestring(field)]
    except KeyError:
        raise ValueError("Unknown field type {0!r}".format(field))


def register_formatter(field_typestr):
    """Decorate a configuration field formatter function to register it with
    the `get_field_formatter` accessor.

    This decorator also performs common helpers for the formatter functions:

    - Does type checking on the field argument passed to a formatter.
    - Assembles a section node from the nodes returned by the formatter.
    """

    def decorator_register(formatter):
        @functools.wraps(formatter)
        def wrapped_formatter(*args, **kwargs):
            field_name = args[0]
            field = args[1]
            field_id = args[2]

            # Before running the formatter, do type checking
            field_type = get_type(field_typestr)
            if not isinstance(field, field_type):
                message = (
                    "Field {0} ({1!r}) is not an " "{2} type. It is an {3}."
                )
                raise ValueError(
                    message.format(
                        field_name, field, field_typestr, typestring(field)
                    )
                )

            # Run the formatter itself
            nodes = formatter(*args, **kwargs)

            # Package nodes from the formatter into a section
            section = make_section(
                section_id=field_id + "-section", contents=nodes
            )
            return section

        FIELD_FORMATTERS[field_typestr] = wrapped_formatter

        return wrapped_formatter

    return decorator_register


@register_formatter("lsst.pex.config.config.Field")
def format_field_nodes(field_name, field, field_id, state, lineno):
    """Create a section node that documents a Field config field.

    Parameters
    ----------
    field_name : `str`
        Name of the configuration field (the attribute name of on the config
        class).
    field : ``lsst.pex.config.Field``
        A configuration field.
    field_id : `str`
        Unique identifier for this field. This is used as the id and name of
        the section node. with a -section suffix
    state : ``docutils.statemachine.State``
        Usually the directive's ``state`` attribute.
    lineno (`int`)
        Usually the directive's ``lineno`` attribute.

    Returns
    -------
    ``docutils.nodes.section``
        Section containing documentation nodes for the Field.
    """
    # Custom Field type item for the definition list
    field_type_item = nodes.definition_list_item()
    field_type_item.append(nodes.term(text="Field type"))
    field_type_item_content = nodes.definition()
    field_type_item_content_p = nodes.paragraph()
    field_type_item_content_p += make_python_xref_nodes_for_type(
        field.dtype, state, hide_namespace=False
    )[0].children[0]
    field_type_item_content_p += nodes.Text(" ", " ")
    field_type_item_content_p += make_python_xref_nodes_for_type(
        type(field), state, hide_namespace=True
    )[0].children[0]
    if field.optional:
        field_type_item_content_p += nodes.Text(" (optional)", " (optional)")
    field_type_item_content += field_type_item_content_p
    field_type_item += field_type_item_content

    # Definition list for key-value metadata
    dl = nodes.definition_list()
    dl += create_default_item_node(field, state)
    dl += field_type_item

    # Doc for this ConfigurableField, parsed as rst
    desc_node = create_description_node(field, state)

    # Title for configuration field
    title = create_title_node(field_name, field, field_id, state, lineno)

    return [title, dl, desc_node]


@register_formatter("lsst.pex.config.configurableField.ConfigurableField")
def format_configurablefield_nodes(field_name, field, field_id, state, lineno):
    """Create a section node that documents a ConfigurableField config field.

    Parameters
    ----------
    field_name : `str`
        Name of the configuration field (the attribute name of on the config
        class).
    field : ``lsst.pex.config.ConfigurableField``
        A configuration field.
    field_id : `str`
        Unique identifier for this field. This is used as the id and name of
        the section node. with a -section suffix
    state : ``docutils.statemachine.State``
        Usually the directive's ``state`` attribute.
    lineno (`int`)
        Usually the directive's ``lineno`` attribute.

    Returns
    -------
    ``docutils.nodes.section``
        Section containing documentation nodes for the ConfigurableField.
    """
    # Custom default target definition list that links to Task topics
    default_item = nodes.definition_list_item()
    default_item.append(nodes.term(text="Default"))
    default_item_content = nodes.definition()
    para = nodes.paragraph()
    name = ".".join((field.target.__module__, field.target.__name__))
    para += pending_task_xref(rawsource=name)
    default_item_content += para
    default_item += default_item_content

    # Definition list for key-value metadata
    dl = nodes.definition_list()
    dl += default_item
    dl += create_field_type_item_node(field, state)

    # Doc for this ConfigurableField, parsed as rst
    desc_node = create_description_node(field, state)

    # Title for configuration field
    title = create_title_node(field_name, field, field_id, state, lineno)

    return [title, dl, desc_node]


@register_formatter("lsst.pex.config.listField.ListField")
def format_listfield_nodes(field_name, field, field_id, state, lineno):
    """Create a section node that documents a ListField config field.

    Parameters
    ----------
    field_name : `str`
        Name of the configuration field (the attribute name of on the config
        class).
    field : ``lsst.pex.config.ListField``
        A configuration field.
    field_id : `str`
        Unique identifier for this field. This is used as the id and name of
        the section node. with a -section suffix
    state : ``docutils.statemachine.State``
        Usually the directive's ``state`` attribute.
    lineno (`int`)
        Usually the directive's ``lineno`` attribute.

    Returns
    -------
    ``docutils.nodes.section``
        Section containing documentation nodes for the ListField.
    """
    # ListField's store their item types in the itemtype attribute
    itemtype_node = nodes.definition_list_item()
    itemtype_node += nodes.term(text="Item type")
    itemtype_def = nodes.definition()
    itemtype_def += make_python_xref_nodes_for_type(
        field.itemtype, state, hide_namespace=False
    )
    itemtype_node += itemtype_def

    minlength_node = None
    if field.minLength:
        minlength_node = nodes.definition_list_item()
        minlength_node += nodes.term(text="Minimum length")
        minlength_def = nodes.definition()
        minlength_def += nodes.paragraph(text=str(field.minLength))
        minlength_node += minlength_def

    maxlength_node = None
    if field.maxLength:
        maxlength_node = nodes.definition_list_item()
        maxlength_node += nodes.term(text="Maximum length")
        maxlength_def = nodes.definition()
        maxlength_def += nodes.paragraph(text=str(field.maxLength))
        maxlength_node += maxlength_def

    length_node = None
    if field.length:
        length_node = nodes.definition_list_item()
        length_node += nodes.term(text="Required length")
        length_def = nodes.definition()
        length_def += nodes.paragraph(text=str(field.length))
        length_node += length_def

    # Type description
    field_type_item = nodes.definition_list_item()
    field_type_item.append(nodes.term(text="Field type"))
    field_type_item_content = nodes.definition()
    field_type_item_content_p = nodes.paragraph()
    field_type_item_content_p += make_python_xref_nodes_for_type(
        field.itemtype, state, hide_namespace=False
    )[0].children[0]
    field_type_item_content_p += nodes.Text(" ", " ")
    field_type_item_content_p += make_python_xref_nodes_for_type(
        type(field), state, hide_namespace=True
    )[0].children[0]
    if field.optional:
        field_type_item_content_p += nodes.Text(" (optional)", " (optional)")
    field_type_item_content += field_type_item_content_p
    field_type_item += field_type_item_content

    # Reference target
    env = state.document.settings.env
    ref_target = create_configfield_ref_target_node(field_id, env, lineno)

    # Title is the field's attribute name
    title = nodes.title(text=field_name)
    title += ref_target

    # Definition list for key-value metadata
    dl = nodes.definition_list()
    dl += create_default_item_node(field, state)
    dl += field_type_item
    if minlength_node:
        dl += minlength_node
    if maxlength_node:
        dl += maxlength_node
    if length_node:
        dl += length_node

    # Doc for this ConfigurableField, parsed as rst
    desc_node = create_description_node(field, state)

    # Title for configuration field
    title = create_title_node(field_name, field, field_id, state, lineno)

    return [title, dl, desc_node]


@register_formatter("lsst.pex.config.choiceField.ChoiceField")
def format_choicefield_nodes(field_name, field, field_id, state, lineno):
    """Create a section node that documents a ChoiceField config field.

    Parameters
    ----------
    field_name : `str`
        Name of the configuration field (the attribute name of on the config
        class).
    field : ``lsst.pex.config.ChoiceField``
        A configuration field.
    field_id : `str`
        Unique identifier for this field. This is used as the id and name of
        the section node. with a -section suffix
    state : ``docutils.statemachine.State``
        Usually the directive's ``state`` attribute.
    lineno (`int`)
        Usually the directive's ``lineno`` attribute.

    Returns
    -------
    ``docutils.nodes.section``
        Section containing documentation nodes for the ChoiceField.
    """
    # Create a definition list for the choices
    choice_dl = nodes.definition_list()
    for choice_value, choice_doc in field.allowed.items():
        item = nodes.definition_list_item()
        item_term = nodes.term()
        item_term += nodes.literal(text=repr(choice_value))
        item += item_term
        item_definition = nodes.definition()
        item_definition.append(nodes.paragraph(text=choice_doc))
        item += item_definition
        choice_dl.append(item)

    choices_node = nodes.definition_list_item()
    choices_node.append(nodes.term(text="Choices"))
    choices_definition = nodes.definition()
    choices_definition.append(choice_dl)
    choices_node.append(choices_definition)

    # Field type
    field_type_item = nodes.definition_list_item()
    field_type_item.append(nodes.term(text="Field type"))
    field_type_item_content = nodes.definition()
    field_type_item_content_p = nodes.paragraph()
    field_type_item_content_p += make_python_xref_nodes_for_type(
        field.dtype, state, hide_namespace=False
    )[0].children[0]
    field_type_item_content_p += nodes.Text(" ", " ")
    field_type_item_content_p += make_python_xref_nodes_for_type(
        type(field), state, hide_namespace=True
    )[0].children[0]
    if field.optional:
        field_type_item_content_p += nodes.Text(" (optional)", " (optional)")
    field_type_item_content += field_type_item_content_p
    field_type_item += field_type_item_content

    # Definition list for key-value metadata
    dl = nodes.definition_list()
    dl += create_default_item_node(field, state)
    dl += field_type_item
    dl += choices_node

    # Doc for this ConfigurableField, parsed as rst
    desc_node = create_description_node(field, state)

    # Title for configuration field
    title = create_title_node(field_name, field, field_id, state, lineno)

    return [title, dl, desc_node]


@register_formatter("lsst.pex.config.rangeField.RangeField")
def format_rangefield_nodes(field_name, field, field_id, state, lineno):
    """Create a section node that documents a RangeField config field.

    Parameters
    ----------
    field_name : `str`
        Name of the configuration field (the attribute name of on the config
        class).
    field : ``lsst.pex.config.RangeField``
        A configuration field.
    field_id : `str`
        Unique identifier for this field. This is used as the id and name of
        the section node. with a -section suffix
    state : ``docutils.statemachine.State``
        Usually the directive's ``state`` attribute.
    lineno (`int`)
        Usually the directive's ``lineno`` attribute.

    Returns
    -------
    ``docutils.nodes.section``
        Section containing documentation nodes for the RangeField.
    """
    # Field type
    field_type_item = nodes.definition_list_item()
    field_type_item.append(nodes.term(text="Field type"))
    field_type_item_content = nodes.definition()
    field_type_item_content_p = nodes.paragraph()
    field_type_item_content_p += make_python_xref_nodes_for_type(
        field.dtype, state, hide_namespace=False
    )[0].children[0]
    field_type_item_content_p += nodes.Text(" ", " ")
    field_type_item_content_p += make_python_xref_nodes_for_type(
        type(field), state, hide_namespace=True
    )[0].children[0]
    if field.optional:
        field_type_item_content_p += nodes.Text(" (optional)", " (optional)")
    field_type_item_content += field_type_item_content_p
    field_type_item += field_type_item_content

    # Format definition list item for the range
    range_node = nodes.definition_list_item()
    range_node += nodes.term(text="Range")
    range_node_def = nodes.definition()
    range_node_def += nodes.paragraph(text=field.rangeString)
    range_node += range_node_def

    # Definition list for key-value metadata
    dl = nodes.definition_list()
    dl += create_default_item_node(field, state)
    dl += field_type_item
    dl += range_node

    # Doc for this field, parsed as rst
    desc_node = create_description_node(field, state)

    # Title for configuration field
    title = create_title_node(field_name, field, field_id, state, lineno)

    return [title, dl, desc_node]


@register_formatter("lsst.pex.config.dictField.DictField")
def format_dictfield_nodes(field_name, field, field_id, state, lineno):
    """Create a section node that documents a DictField config field.

    Parameters
    ----------
    field_name : `str`
        Name of the configuration field (the attribute name of on the config
        class).
    field : ``lsst.pex.config.DictField``
        A configuration field.
    field_id : `str`
        Unique identifier for this field. This is used as the id and name of
        the section node. with a -section suffix
    state : ``docutils.statemachine.State``
        Usually the directive's ``state`` attribute.
    lineno (`int`)
        Usually the directive's ``lineno`` attribute.

    Returns
    -------
    ``docutils.nodes.section``
        Section containing documentation nodes for the DictField.
    """
    # Custom value type field for definition list
    valuetype_item = nodes.definition_list_item()
    valuetype_item = nodes.term(text="Value type")
    valuetype_def = nodes.definition()
    valuetype_def += make_python_xref_nodes_for_type(
        field.itemtype, state, hide_namespace=False
    )
    valuetype_item += valuetype_def

    # Definition list for key-value metadata
    dl = nodes.definition_list()
    dl += create_default_item_node(field, state)
    dl += create_field_type_item_node(field, state)
    dl += create_keytype_item_node(field, state)
    dl += valuetype_item

    # Doc for this field, parsed as rst
    desc_node = create_description_node(field, state)

    # Title for configuration field
    title = create_title_node(field_name, field, field_id, state, lineno)

    return [title, dl, desc_node]


@register_formatter("lsst.pex.config.configField.ConfigField")
def format_configfield_nodes(field_name, field, field_id, state, lineno):
    """Create a section node that documents a ConfigField config field.

    Parameters
    ----------
    field_name : `str`
        Name of the configuration field (the attribute name of on the config
        class).
    field : ``lsst.pex.config.ConfigField``
        A configuration field.
    field_id : `str`
        Unique identifier for this field. This is used as the id and name of
        the section node. with a -section suffix
    state : ``docutils.statemachine.State``
        Usually the directive's ``state`` attribute.
    lineno (`int`)
        Usually the directive's ``lineno`` attribute.

    Returns
    -------
    ``docutils.nodes.section``
        Section containing documentation nodes for the ConfigField.
    """
    # Default data type node
    dtype_node = nodes.definition_list_item()
    dtype_node = nodes.term(text="Data type")
    dtype_def = nodes.definition()
    dtype_def_para = nodes.paragraph()
    name = ".".join((field.dtype.__module__, field.dtype.__name__))
    dtype_def_para += pending_config_xref(rawsource=name)
    dtype_def += dtype_def_para
    dtype_node += dtype_def

    # Definition list for key-value metadata
    dl = nodes.definition_list()
    dl += dtype_node
    dl += create_field_type_item_node(field, state)

    # Doc for this field, parsed as rst
    desc_node = create_description_node(field, state)

    # Title for configuration field
    title = create_title_node(field_name, field, field_id, state, lineno)

    return [title, dl, desc_node]


@register_formatter("lsst.pex.config.configChoiceField.ConfigChoiceField")
def format_configchoicefield_nodes(field_name, field, field_id, state, lineno):
    """Create a section node that documents a ConfigChoiceField config field.

    Parameters
    ----------
    field_name : `str`
        Name of the configuration field (the attribute name of on the config
        class).
    field : ``lsst.pex.config.ConfigChoiceField``
        A configuration field.
    field_id : `str`
        Unique identifier for this field. This is used as the id and name of
        the section node. with a -section suffix
    state : ``docutils.statemachine.State``
        Usually the directive's ``state`` attribute.
    lineno (`int`)
        Usually the directive's ``lineno`` attribute.

    Returns
    -------
    ``docutils.nodes.section``
        Section containing documentation nodes for the ConfigChoiceField.
    """
    # Create a definition list for the choices
    choice_dl = nodes.definition_list()
    for choice_value, choice_class in field.typemap.items():
        item = nodes.definition_list_item()
        item_term = nodes.term()
        item_term += nodes.literal(text=repr(choice_value))
        item += item_term
        item_definition = nodes.definition()
        def_para = nodes.paragraph()
        name = ".".join((choice_class.__module__, choice_class.__name__))
        def_para += pending_config_xref(rawsource=name)
        item_definition += def_para
        item += item_definition
        choice_dl.append(item)

    choices_node = nodes.definition_list_item()
    choices_node.append(nodes.term(text="Choices"))
    choices_definition = nodes.definition()
    choices_definition.append(choice_dl)
    choices_node.append(choices_definition)

    # Field type
    field_type_item = nodes.definition_list_item()
    field_type_item.append(nodes.term(text="Field type"))
    field_type_item_content = nodes.definition()
    field_type_item_content_p = nodes.paragraph()
    if field.multi:
        multi_text = "Multi-selection "
    else:
        multi_text = "Single-selection "
    field_type_item_content_p += nodes.Text(multi_text, multi_text)
    field_type_item_content_p += make_python_xref_nodes_for_type(
        type(field), state, hide_namespace=True
    )[0].children[0]
    if field.optional:
        field_type_item_content_p += nodes.Text(" (optional)", " (optional)")
    field_type_item_content += field_type_item_content_p
    field_type_item += field_type_item_content

    dl = nodes.definition_list()
    dl += create_default_item_node(field, state)
    dl += field_type_item
    dl += choices_node

    # Doc for this field, parsed as rst
    desc_node = create_description_node(field, state)

    # Title for configuration field
    title = create_title_node(field_name, field, field_id, state, lineno)

    return [title, dl, desc_node]


@register_formatter("lsst.pex.config.configDictField.ConfigDictField")
def format_configdictfield_nodes(field_name, field, field_id, state, lineno):
    """Create a section node that documents a ConfigDictField config field.

    Parameters
    ----------
    field_name : `str`
        Name of the configuration field (the attribute name of on the config
        class).
    field : ``lsst.pex.config.ConfigDictField``
        A configuration field.
    field_id : `str`
        Unique identifier for this field. This is used as the id and name of
        the section node. with a -section suffix
    state : ``docutils.statemachine.State``
        Usually the directive's ``state`` attribute.
    lineno (`int`)
        Usually the directive's ``lineno`` attribute.

    Returns
    -------
    ``docutils.nodes.section``
        Section containing documentation nodes for the ConfigDictField.
    """
    # Valuetype links to a Config task topic
    value_item = nodes.definition_list_item()
    value_item += nodes.term(text="Value type")
    value_item_def = nodes.definition()
    value_item_def_para = nodes.paragraph()
    name = ".".join((field.itemtype.__module__, field.itemtype.__name__))
    value_item_def_para += pending_config_xref(rawsource=name)
    value_item_def += value_item_def_para
    value_item += value_item_def

    dl = nodes.definition_list()
    dl += create_default_item_node(field, state)
    dl += create_field_type_item_node(field, state)
    dl += create_keytype_item_node(field, state)
    dl += value_item

    # Doc for this field, parsed as rst
    desc_node = create_description_node(field, state)

    # Title for configuration field
    title = create_title_node(field_name, field, field_id, state, lineno)

    return [title, dl, desc_node]


@register_formatter("lsst.pex.config.registry.RegistryField")
def format_registryfield_nodes(field_name, field, field_id, state, lineno):
    """Create a section node that documents a RegistryField config field.

    Parameters
    ----------
    field_name : `str`
        Name of the configuration field (the attribute name of on the config
        class).
    field : ``lsst.pex.config.RegistryField``
        A configuration field.
    field_id : `str`
        Unique identifier for this field. This is used as the id and name of
        the section node. with a -section suffix
    state : ``docutils.statemachine.State``
        Usually the directive's ``state`` attribute.
    lineno (`int`)
        Usually the directive's ``lineno`` attribute.

    Returns
    -------
    ``docutils.nodes.section``
        Section containing documentation nodes for the RegistryField.
    """
    from lsst.pex.config.registry import ConfigurableWrapper

    # Create a definition list for the choices
    # This iteration is over field.registry.items(), not field.items(), so
    # that the directive shows the configurables, not their ConfigClasses.
    choice_dl = nodes.definition_list()
    for choice_value, choice_class in field.registry.items():
        # Introspect the class name from item in the registry. This is harder
        # than it should be. Most registry items seem to fall in the first
        # category. Some are ConfigurableWrapper types that expose the
        # underlying task class through the _target attribute.
        if hasattr(choice_class, "__module__") and hasattr(
            choice_class, "__name__"
        ):
            name = ".".join((choice_class.__module__, choice_class.__name__))
        elif isinstance(choice_class, ConfigurableWrapper):
            name = ".".join(
                (
                    choice_class._target.__class__.__module__,
                    choice_class._target.__class__.__name__,
                )
            )
        else:
            name = ".".join(
                (
                    choice_class.__class__.__module__,
                    choice_class.__class__.__name__,
                )
            )

        item = nodes.definition_list_item()
        item_term = nodes.term()
        item_term += nodes.literal(text=repr(choice_value))
        item += item_term
        item_definition = nodes.definition()
        def_para = nodes.paragraph()
        def_para += pending_task_xref(rawsource=name)
        item_definition += def_para
        item += item_definition
        choice_dl.append(item)

    choices_node = nodes.definition_list_item()
    choices_node.append(nodes.term(text="Choices"))
    choices_definition = nodes.definition()
    choices_definition.append(choice_dl)
    choices_node.append(choices_definition)

    # Field type
    field_type_item = nodes.definition_list_item()
    field_type_item.append(nodes.term(text="Field type"))
    field_type_item_content = nodes.definition()
    field_type_item_content_p = nodes.paragraph()
    if field.multi:
        multi_text = "Multi-selection "
    else:
        multi_text = "Single-selection "
    field_type_item_content_p += nodes.Text(multi_text, multi_text)
    field_type_item_content_p += make_python_xref_nodes_for_type(
        type(field), state, hide_namespace=True
    )[0].children[0]
    if field.optional:
        field_type_item_content_p += nodes.Text(" (optional)", " (optional)")
    field_type_item_content += field_type_item_content_p
    field_type_item += field_type_item_content

    dl = nodes.definition_list()
    dl += create_default_item_node(field, state)
    dl += field_type_item
    dl += choices_node

    # Doc for this field, parsed as rst
    desc_node = create_description_node(field, state)

    # Title for configuration field
    title = create_title_node(field_name, field, field_id, state, lineno)

    return [title, dl, desc_node]


def create_field_type_item_node(field, state):
    """Create a definition list item node that describes a field's type.

    Parameters
    ----------
    field : ``lsst.pex.config.Field``
        A configuration field.
    state : ``docutils.statemachine.State``
        Usually the directive's ``state`` attribute.

    Returns
    -------
    ``docutils.nodes.definition_list_item``
        Definition list item that describes a field's type.
    """
    type_item = nodes.definition_list_item()
    type_item.append(nodes.term(text="Field type"))
    type_item_content = nodes.definition()
    type_item_content_p = nodes.paragraph()
    type_item_content_p += make_python_xref_nodes_for_type(
        type(field), state, hide_namespace=True
    )[0].children
    if field.optional:
        type_item_content_p += nodes.Text(" (optional)", " (optional)")
    type_item_content += type_item_content_p
    type_item += type_item_content
    return type_item


def create_default_item_node(field, state):
    """Create a definition list item node that describes the default value
    of a Field config.

    Parameters
    ----------
    field : ``lsst.pex.config.Field``
        A configuration field.
    state : ``docutils.statemachine.State``
        Usually the directive's ``state`` attribute.

    Returns
    -------
    ``docutils.nodes.definition_list_item``
        Definition list item that describes the default target of a
        ConfigurableField config.
    """
    default_item = nodes.definition_list_item()
    default_item.append(nodes.term(text="Default"))
    default_item_content = nodes.definition()
    default_item_content.append(nodes.literal(text=repr(field.default)))
    default_item.append(default_item_content)
    return default_item


def create_keytype_item_node(field, state):
    """Create a definition list item node that describes the key type
    of a dict-type config field.

    Parameters
    ----------
    field : ``lsst.pex.config.Field``
        A ``lsst.pex.config.DictField`` or ``lsst.pex.config.DictConfigField``.
    state : ``docutils.statemachine.State``
        Usually the directive's ``state`` attribute.

    Returns
    -------
    ``docutils.nodes.definition_list_item``
        Definition list item that describes the key type for the field.
    """
    keytype_node = nodes.definition_list_item()
    keytype_node = nodes.term(text="Key type")
    keytype_def = nodes.definition()
    keytype_def += make_python_xref_nodes_for_type(
        field.keytype, state, hide_namespace=False
    )
    keytype_node += keytype_def
    return keytype_node


def create_description_node(field, state):
    """Creates docutils nodes for the Field's description, built from the
    field's ``doc`` and ``optional`` attributes.

    Parameters
    ----------
    field : ``lsst.pex.config.Field``
        A configuration field.
    state : ``docutils.statemachine.State``
        Usually the directive's ``state`` attribute.

    Returns
    -------
    ``docutils.nodes.section``
        Section containing nodes for the description of the ``field``.
    """
    doc_container_node = nodes.container()
    doc_container_node += parse_rst_content(field.doc, state)

    return doc_container_node


def create_title_node(field_name, field, field_id, state, lineno):
    """Create docutils nodes for the configuration field's title and
    reference target node.

    Parameters
    ----------
    field : ``lsst.pex.config.Field``
        A configuration field.
    state : ``docutils.statemachine.State``
        Usually the directive's ``state`` attribute.

    Returns
    -------
    ``docutils.nodes.title``
        Title containing nodes for the title of the ``field`` and reference
        target.
    """
    # Reference target
    env = state.document.settings.env
    ref_target = create_configfield_ref_target_node(field_id, env, lineno)

    # Title is the field's attribute name
    title = nodes.title(text=field_name)
    title += ref_target

    return title


def create_configfield_ref_target_node(target_id, env, lineno):
    """Create a ``target`` node that marks a configuration field.

    Internally, this also adds to the ``lsst_configfields`` attribute of the
    environment that is consumed by `documenteer.sphinxext.lssttasks.
    crossrefs.process_pending_configfield_xref_nodes`.

    See also
    --------
    `documenteer.sphinxext.lssttasks.crossrefs.process_pending_configfield_xref_nodes`
    """
    target_node = nodes.target("", "", ids=[target_id])

    # Store these task/configurable topic nodes in the environment for later
    # cross referencing.
    if not hasattr(env, "lsst_configfields"):
        env.lsst_configfields = {}
    env.lsst_configfields[target_id] = {
        "docname": env.docname,
        "lineno": lineno,
        "target": target_node,
    }

    return target_node
