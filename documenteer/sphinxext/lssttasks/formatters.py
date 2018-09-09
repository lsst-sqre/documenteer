"""Docutils formatters for different Task and Task configuration objects.
"""

__all__ = (
    'get_field_formatter', 'format_field_nodes',
    'format_configurablefield_nodes', 'format_listfield_nodes',
    'format_choicefield_nodes', 'format_rangefield_nodes',
    'format_dictfield_nodes', 'format_configfield_nodes',
    'format_configchoicefield_nodes', 'format_configdictfield_nodes',
    'format_registryfield_nodes', 'create_dtype_item_node',
    'create_field_type_item_node', 'create_default_item_node',
    'create_default_target_item_node', 'create_keytype_item_node',
    'create_valuetype_item_node', 'create_description_node'
)

from docutils import nodes

from ..utils import (parse_rst_content, make_python_xref_nodes_for_type,
                     make_section)
from .taskutils import typestring
from .crossrefs import pending_task_xref, pending_config_xref


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
        section_id (`str`)
            Unique identifier for this field. This is used as the id and name
            of the section node.
        state (``docutils.statemachine.State``)
            Usually the directive's ``state`` attribute.

    Raises
    ------
    ValueError
        Raised if the field type is unknown.
    """
    try:
        return FIELD_FORMATTERS[typestring(field)]
    except KeyError:
        raise ValueError('Unknown field type {0!r}'.format(field))


def format_field_nodes(field_name, field, section_id, state):
    """Create a section node that documents a Field config field.

    Parameters
    ----------
    field_name : `str`
        Name of the configuration field (the attribute name of on the config
        class).
    field : ``lsst.pex.config.Field``
        A configuration field.
    section_id : `str`
        Unique identifier for this field. This is used as the id and name of
        the section node.
    state : ``docutils.statemachine.State``
        Usually the directive's ``state`` attribute.

    Returns
    -------
    ``docutils.nodes.section``
        Section containing documentation nodes for the Field.
    """
    from lsst.pex.config import Field
    if not isinstance(field, Field):
        message = ('Field {0} ({1!r}) is not an '
                   'lsst.pex.config.Field type. It is an {2!s}.')
        raise ValueError(message.format(field_name, field, type(field)))

    # Title is the field's attribute name
    title = nodes.title(text=field_name)

    dl = nodes.definition_list()
    dl += create_default_item_node(field, state)
    dl += create_dtype_item_node(field, state)
    dl += create_field_type_item_node(field, state)

    # Doc for this ConfigurableField, parsed as rst
    desc_node = create_description_node(field, state)

    # Package all the nodes into a `section`
    section = make_section(
        section_id=section_id,
        contents=[title, dl, desc_node])

    return section


def format_configurablefield_nodes(field_name, field, section_id, state):
    """Create a section node that documents a ConfigurableField config field.

    Parameters
    ----------
    field_name : `str`
        Name of the configuration field (the attribute name of on the config
        class).
    field : ``lsst.pex.config.ConfigurableField``
        A configuration field.
    section_id : `str`
        Unique identifier for this field. This is used as the id and name of
        the section node.
    state : ``docutils.statemachine.State``
        Usually the directive's ``state`` attribute.

    Returns
    -------
    ``docutils.nodes.section``
        Section containing documentation nodes for the ConfigurableField.
    """
    from lsst.pex.config import ConfigurableField
    if not isinstance(field, ConfigurableField):
        message = ('Field {0} ({1!r}) is not an '
                   'lsst.pex.config.ConfigurableField type. It is an {2!s}.')
        raise ValueError(message.format(field_name, field, type(field)))

    # Title is the field's attribute name
    title = nodes.title(text=field_name)

    dl = nodes.definition_list()
    dl += create_default_target_item_node(field, state)
    dl += create_field_type_item_node(field, state)

    # Doc for this ConfigurableField, parsed as rst
    desc_node = create_description_node(field, state)

    # Package all the nodes into a `section`
    section = make_section(
        section_id=section_id,
        contents=[title, dl, desc_node])

    return section


def format_listfield_nodes(field_name, field, section_id, state):
    """Create a section node that documents a ListField config field.

    Parameters
    ----------
    field_name : `str`
        Name of the configuration field (the attribute name of on the config
        class).
    field : ``lsst.pex.config.ListField``
        A configuration field.
    section_id : `str`
        Unique identifier for this field. This is used as the id and name of
        the section node.
    state : ``docutils.statemachine.State``
        Usually the directive's ``state`` attribute.

    Returns
    -------
    ``docutils.nodes.section``
        Section containing documentation nodes for the ListField.
    """
    from lsst.pex.config import ListField
    if not isinstance(field, ListField):
        message = ('Field {0} ({1!r}) is not an '
                   'lsst.pex.config.ListField type. It is an {2!s}.')
        raise ValueError(message.format(field_name, field, type(field)))

    # ListField's store their item types in the itemtype attribute
    itemtype_node = nodes.definition_list_item()
    itemtype_node += nodes.term(text='Item type')
    itemtype_def = nodes.definition()
    itemtype_def += make_python_xref_nodes_for_type(
        field.itemtype,
        state,
        hide_namespace=False)
    itemtype_node += itemtype_def

    minlength_node = None
    if field.minLength:
        minlength_node = nodes.definition_list_item()
        minlength_node += nodes.term(text='Minimum length')
        minlength_def = nodes.definition()
        minlength_def += nodes.paragraph(text=str(field.minLength))
        minlength_node += minlength_def

    maxlength_node = None
    if field.maxLength:
        maxlength_node = nodes.definition_list_item()
        maxlength_node += nodes.term(text='Maximum length')
        maxlength_def = nodes.definition()
        maxlength_def += nodes.paragraph(text=str(field.maxLength))
        maxlength_node += maxlength_def

    length_node = None
    if field.length:
        length_node = nodes.definition_list_item()
        length_node += nodes.term(text='Required length')
        length_def = nodes.definition()
        length_def += nodes.paragraph(text=str(field.length))
        length_node += length_def

    # Title is the field's attribute name
    title = nodes.title(text=field_name)

    dl = nodes.definition_list()
    dl += create_default_item_node(field, state)
    dl += itemtype_node
    dl += create_field_type_item_node(field, state)
    if minlength_node:
        dl += minlength_node
    if maxlength_node:
        dl += maxlength_node
    if length_node:
        dl += length_node

    # Doc for this ConfigurableField, parsed as rst
    desc_node = create_description_node(field, state)

    # Package all the nodes into a `section`
    section = make_section(
        section_id=section_id,
        contents=[title, dl, desc_node])

    return section


def format_choicefield_nodes(field_name, field, section_id, state):
    """Create a section node that documents a ChoiceField config field.

    Parameters
    ----------
    field_name : `str`
        Name of the configuration field (the attribute name of on the config
        class).
    field : ``lsst.pex.config.ChoiceField``
        A configuration field.
    section_id : `str`
        Unique identifier for this field. This is used as the id and name of
        the section node.
    state : ``docutils.statemachine.State``
        Usually the directive's ``state`` attribute.

    Returns
    -------
    ``docutils.nodes.section``
        Section containing documentation nodes for the ChoiceField.
    """
    from lsst.pex.config import ChoiceField
    if not isinstance(field, ChoiceField):
        message = ('Field {0} ({1!r}) is not an lsst.pex.config.ChoiceField '
                   'type. It is an {2!s}.')
        raise ValueError(message.format(field_name, field, type(field)))

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
    choices_node.append(nodes.term(text='Choices'))
    choices_definition = nodes.definition()
    choices_definition.append(choice_dl)
    choices_node.append(choices_definition)

    # Title is the field's attribute name
    title = nodes.title(text=field_name)

    dl = nodes.definition_list()
    dl += create_default_item_node(field, state)
    dl += choices_node
    dl += create_dtype_item_node(field, state)
    dl += create_field_type_item_node(field, state)

    # Doc for this ConfigurableField, parsed as rst
    desc_node = create_description_node(field, state)

    # Package all the nodes into a `section`
    section = make_section(
        section_id=section_id,
        contents=[title, dl, desc_node])

    return section


def format_rangefield_nodes(field_name, field, section_id, state):
    """Create a section node that documents a RangeField config field.

    Parameters
    ----------
    field_name : `str`
        Name of the configuration field (the attribute name of on the config
        class).
    field : ``lsst.pex.config.RangeField``
        A configuration field.
    section_id : `str`
        Unique identifier for this field. This is used as the id and name of
        the section node.
    state : ``docutils.statemachine.State``
        Usually the directive's ``state`` attribute.

    Returns
    -------
    ``docutils.nodes.section``
        Section containing documentation nodes for the RangeField.
    """
    from lsst.pex.config import RangeField
    if not isinstance(field, RangeField):
        message = ('Field {0} ({1!r}) is not an lsst.pex.config.RangeField '
                   'type. It is an {2!s}.')
        raise ValueError(message.format(field_name, field, type(field)))

    # Format definition list item for the range
    range_node = nodes.definition_list_item()
    range_node += nodes.term(text='Range')
    range_node_def = nodes.definition()
    range_node_def += nodes.paragraph(text=field.rangeString)
    range_node += range_node_def

    # Title is the field's attribute name
    title = nodes.title(text=field_name)

    dl = nodes.definition_list()
    dl += create_default_item_node(field, state)
    dl += range_node
    dl += create_dtype_item_node(field, state)
    dl += create_field_type_item_node(field, state)

    # Doc for this field, parsed as rst
    desc_node = create_description_node(field, state)

    # Package all the nodes into a `section`
    section = make_section(
        section_id=section_id,
        contents=[title, dl, desc_node])

    return section


def format_dictfield_nodes(field_name, field, section_id, state):
    """Create a section node that documents a DictField config field.

    Parameters
    ----------
    field_name : `str`
        Name of the configuration field (the attribute name of on the config
        class).
    field : ``lsst.pex.config.DictField``
        A configuration field.
    section_id : `str`
        Unique identifier for this field. This is used as the id and name of
        the section node.
    state : ``docutils.statemachine.State``
        Usually the directive's ``state`` attribute.

    Returns
    -------
    ``docutils.nodes.section``
        Section containing documentation nodes for the DictField.
    """
    from lsst.pex.config import DictField
    if not isinstance(field, DictField):
        message = ('Field {0} ({1!r}) is not an lsst.pex.config.DictField '
                   'type. It is an {2!s}.')
        raise ValueError(message.format(field_name, field, type(field)))

    # Title is the field's attribute name
    title = nodes.title(text=field_name)

    dl = nodes.definition_list()
    dl += create_default_item_node(field, state)
    dl += create_keytype_item_node(field, state)
    dl += create_valuetype_item_node(field, state)
    dl += create_field_type_item_node(field, state)

    # Doc for this field, parsed as rst
    desc_node = create_description_node(field, state)

    # Package all the nodes into a `section`
    section = make_section(
        section_id=section_id,
        contents=[title, dl, desc_node])

    return section


def format_configfield_nodes(field_name, field, section_id, state):
    """Create a section node that documents a ConfigField config field.

    Parameters
    ----------
    field_name : `str`
        Name of the configuration field (the attribute name of on the config
        class).
    field : ``lsst.pex.config.ConfigField``
        A configuration field.
    section_id : `str`
        Unique identifier for this field. This is used as the id and name of
        the section node.
    state : ``docutils.statemachine.State``
        Usually the directive's ``state`` attribute.

    Returns
    -------
    ``docutils.nodes.section``
        Section containing documentation nodes for the ConfigField.
    """
    from lsst.pex.config import ConfigField
    if not isinstance(field, ConfigField):
        message = ('Field {0} ({1!r}) is not an lsst.pex.config.ConfigField '
                   'type. It is an {2!s}.')
        raise ValueError(message.format(field_name, field, type(field)))

    # Default configuration node
    default_config_node = nodes.definition_list_item()
    default_config_node = nodes.term(text='Default')
    default_config_def = nodes.definition()
    default_config_def_para = nodes.paragraph()
    name = '.'.join((field.default.__module__, field.default.__name__))
    default_config_def_para += pending_config_xref(rawsource=name)
    default_config_def += default_config_def_para
    default_config_node += default_config_def

    # Default data type node
    dtype_node = nodes.definition_list_item()
    dtype_node = nodes.term(text='Data type')
    dtype_def = nodes.definition()
    dtype_def_para = nodes.paragraph()
    name = '.'.join((field.dtype.__module__, field.dtype.__name__))
    dtype_def_para += pending_config_xref(rawsource=name)
    dtype_def += dtype_def_para
    dtype_node += dtype_def

    # Title is the field's attribute name
    title = nodes.title(text=field_name)

    dl = nodes.definition_list()
    dl += default_config_node
    dl += dtype_node
    dl += create_field_type_item_node(field, state)

    # Doc for this field, parsed as rst
    desc_node = create_description_node(field, state)

    # Package all the nodes into a `section`
    section = make_section(
        section_id=section_id,
        contents=[title, dl, desc_node])

    return section


def format_configchoicefield_nodes(field_name, field, section_id, state):
    """Create a section node that documents a ConfigChoiceField config field.

    Parameters
    ----------
    field_name : `str`
        Name of the configuration field (the attribute name of on the config
        class).
    field : ``lsst.pex.config.ConfigChoiceField``
        A configuration field.
    section_id : `str`
        Unique identifier for this field. This is used as the id and name of
        the section node.
    state : ``docutils.statemachine.State``
        Usually the directive's ``state`` attribute.

    Returns
    -------
    ``docutils.nodes.section``
        Section containing documentation nodes for the ConfigChoiceField.
    """
    from lsst.pex.config import ConfigChoiceField
    if not isinstance(field, ConfigChoiceField):
        message = ('Field {0} ({1!r}) is not an '
                   'lsst.pex.config.ConfigChoiceField type. It is an {2!s}.')
        raise ValueError(message.format(field_name, field, type(field)))

    # Create a definition list for the choices
    choice_dl = nodes.definition_list()
    for choice_value, choice_class in field.typemap.items():
        item = nodes.definition_list_item()
        item_term = nodes.term()
        item_term += nodes.literal(text=repr(choice_value))
        item += item_term
        item_definition = nodes.definition()
        def_para = nodes.paragraph()
        name = '.'.join((choice_class.__module__, choice_class.__name__))
        def_para += pending_config_xref(rawsource=name)
        item_definition += def_para
        item += item_definition
        choice_dl.append(item)

    choices_node = nodes.definition_list_item()
    choices_node.append(nodes.term(text='Choices'))
    choices_definition = nodes.definition()
    choices_definition.append(choice_dl)
    choices_node.append(choices_definition)

    # Title is the field's attribute name
    title = nodes.title(text=field_name)

    dl = nodes.definition_list()
    dl += create_default_item_node(field, state)
    dl += choices_node
    dl += create_dtype_item_node(field, state)
    dl += create_field_type_item_node(field, state)
    dl += create_multiple_selections_node(field, state)

    # Doc for this field, parsed as rst
    desc_node = create_description_node(field, state)

    # Package all the nodes into a `section`
    section = make_section(
        section_id=section_id,
        contents=[title, dl, desc_node])

    return section


def format_configdictfield_nodes(field_name, field, section_id, state):
    """Create a section node that documents a ConfigDictField config field.

    Parameters
    ----------
    field_name : `str`
        Name of the configuration field (the attribute name of on the config
        class).
    field : ``lsst.pex.config.ConfigDictField``
        A configuration field.
    section_id : `str`
        Unique identifier for this field. This is used as the id and name of
        the section node.
    state : ``docutils.statemachine.State``
        Usually the directive's ``state`` attribute.

    Returns
    -------
    ``docutils.nodes.section``
        Section containing documentation nodes for the ConfigDictField.
    """
    from lsst.pex.config import ConfigDictField
    if not isinstance(field, ConfigDictField):
        message = ('Field {0} ({1!r}) is not an '
                   'lsst.pex.config.ConfigDictField type. It is an {2!s}.')
        raise ValueError(message.format(field_name, field, type(field)))

    # Valuetype links to a Config task topic
    value_item = nodes.definition_list_item()
    value_item += nodes.term(text="Value type")
    value_item_def = nodes.definition()
    value_item_def_para = nodes.paragraph()
    name = '.'.join((field.itemtype.__module__, field.itemtype.__name__))
    value_item_def_para += pending_config_xref(rawsource=name)
    value_item_def += value_item_def_para
    value_item += value_item_def

    # Title is the field's attribute name
    title = nodes.title(text=field_name)

    dl = nodes.definition_list()
    dl += create_default_item_node(field, state)
    dl += create_keytype_item_node(field, state)
    dl += value_item
    dl += create_field_type_item_node(field, state)

    # Doc for this field, parsed as rst
    desc_node = create_description_node(field, state)

    # Package all the nodes into a `section`
    section = make_section(
        section_id=section_id,
        contents=[title, dl, desc_node])

    return section


def format_registryfield_nodes(field_name, field, section_id, state):
    """Create a section node that documents a RegistryField config field.

    Parameters
    ----------
    field_name : `str`
        Name of the configuration field (the attribute name of on the config
        class).
    field : ``lsst.pex.config.RegistryField``
        A configuration field.
    section_id : `str`
        Unique identifier for this field. This is used as the id and name of
        the section node.
    state : ``docutils.statemachine.State``
        Usually the directive's ``state`` attribute.

    Returns
    -------
    ``docutils.nodes.section``
        Section containing documentation nodes for the RegistryField.
    """
    from lsst.pex.config import RegistryField
    if not isinstance(field, RegistryField):
        message = ('Field {0} ({1!r}) is not an '
                   'lsst.pex.config.RegistryField type. It is an {2!s}.')
        raise ValueError(message.format(field_name, field, type(field)))

    # Create a definition list for the choices
    # This iteration is over field.registry.items(), not field.items(), so
    # that the directive shows the configurables, not their ConfigClasses.
    choice_dl = nodes.definition_list()
    for choice_value, choice_class in field.registry.items():
        item = nodes.definition_list_item()
        item_term = nodes.term()
        item_term += nodes.literal(text=repr(choice_value))
        item += item_term
        item_definition = nodes.definition()
        def_para = nodes.paragraph()
        name = '.'.join((choice_class.__module__, choice_class.__name__))
        def_para += pending_task_xref(rawsource=name)
        item_definition += def_para
        item += item_definition
        choice_dl.append(item)

    choices_node = nodes.definition_list_item()
    choices_node.append(nodes.term(text='Choices'))
    choices_definition = nodes.definition()
    choices_definition.append(choice_dl)
    choices_node.append(choices_definition)

    # Title is the field's attribute name
    title = nodes.title(text=field_name)

    dl = nodes.definition_list()
    dl += create_default_item_node(field, state)
    dl += choices_node
    dl += create_field_type_item_node(field, state)
    dl += create_multiple_selections_node(field, state)

    # Doc for this field, parsed as rst
    desc_node = create_description_node(field, state)

    # Package all the nodes into a `section`
    section = make_section(
        section_id=section_id,
        contents=[title, dl, desc_node])

    return section


def create_dtype_item_node(field, state):
    """Create a definition list item node that describes a field's dtype.

    Parameters
    ----------
    field : ``lsst.pex.config.Field``
        A configuration field.
    state : ``docutils.statemachine.State``
        Usually the directive's ``state`` attribute.

    Returns
    -------
    ``docutils.nodes.definition_list_item``
        Definition list item that describes a field's data type.
    """
    type_item = nodes.definition_list_item()
    type_item.append(nodes.term(text="Data type"))
    type_item_content = nodes.definition()
    type_item_content += make_python_xref_nodes_for_type(
        field.dtype,
        state,
        hide_namespace=False)
    type_item.append(type_item_content)
    return type_item


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
    type_item_content += make_python_xref_nodes_for_type(
        type(field),
        state,
        hide_namespace=True)
    type_item.append(type_item_content)
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
    default_item_content.append(
        nodes.literal(text=repr(field.default))
    )
    default_item.append(default_item_content)
    return default_item


def create_default_target_item_node(field, state):
    """Create a definition list item node that describes the default target
    of a ConfigurableField config.

    Parameters
    ----------
    field : ``lsst.pex.config.ConfigurableField``
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
    para = nodes.paragraph()
    name = '.'.join((field.target.__module__, field.target.__name__))
    para += pending_task_xref(rawsource=name)
    default_item_content += para
    default_item += default_item_content
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
    keytype_node = nodes.term(text='Key type')
    keytype_def = nodes.definition()
    keytype_def += make_python_xref_nodes_for_type(
        field.keytype,
        state,
        hide_namespace=False)
    keytype_node += keytype_def
    return keytype_node


def create_valuetype_item_node(field, state):
    """Create a definition list item node that describes the value type
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
        Definition list item that describes the value type for the field.
    """
    valuetype_node = nodes.definition_list_item()
    valuetype_node = nodes.term(text='Value type')
    valuetype_def = nodes.definition()
    valuetype_def += make_python_xref_nodes_for_type(
        field.itemtype,
        state,
        hide_namespace=False)
    valuetype_node += valuetype_def
    return valuetype_node


def create_multiple_selections_node(field, state):
    """Create a definition list item node that describes whether multiple
    selections are allowed for a ConfigChoiceField.

    Parameters
    ----------
    field : ``lsst.pex.config.ConfigChoiceField``
        An ``lsst.pex.config.ConfigChoiceField`` configuration field.
    state : ``docutils.statemachine.State``
        Usually the directive's ``state`` attribute.

    Returns
    -------
    ``docutils.nodes.definition_list_item``
        Definition list item that describes with a term "Multiple selections."
    """
    default_item = nodes.definition_list_item()
    default_item += nodes.term(text="Multiple selections")
    default_item_content = nodes.definition()
    if field.multi:
        default_item_content += nodes.paragraph(
            text='Allowed')
    else:
        default_item_content += nodes.paragraph(
            text='Disallowed')
    default_item += default_item_content
    return default_item


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
        Section containing nodes for the ``field``\ 's description.
    """
    doc_container_node = nodes.container()
    doc_container_node += parse_rst_content(field.doc, state)

    # Augment documentation paragraph if the field is optional
    if field.optional:
        optional_para = nodes.paragraph(text="Optional.")
        doc_container_node.append(optional_para)

    return doc_container_node


FIELD_FORMATTERS = {
    'lsst.pex.config.configurableField.ConfigurableField':
        format_configurablefield_nodes,
    'lsst.pex.config.config.Field':
        format_field_nodes,
    'lsst.pex.config.listField.ListField':
        format_listfield_nodes,
    'lsst.pex.config.choiceField.ChoiceField':
        format_choicefield_nodes,
    'lsst.pex.config.rangeField.RangeField':
        format_rangefield_nodes,
    'lsst.pex.config.dictField.DictField':
        format_dictfield_nodes,
    'lsst.pex.config.configField.ConfigField':
        format_configfield_nodes,
    'lsst.pex.config.configChoiceField.ConfigChoiceField':
        format_configchoicefield_nodes,
    'lsst.pex.config.configDictField.ConfigDictField':
        format_configdictfield_nodes,
    'lsst.pex.config.registry.RegistryField':
        format_registryfield_nodes,
}
