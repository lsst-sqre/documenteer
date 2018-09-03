"""Docutils formatters for different Task and Task configuration objects.
"""

__all__ = (
    'get_field_formatter', 'format_configurablefield_nodes',
    'create_field_type_item_node', 'create_default_target_item_node',
    'create_description_node'
)

from docutils import nodes

from ..utils import parse_rst_content, make_python_xref_nodes, make_section
from .taskutils import typestring


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
    field_type = typestring(field)
    type_item_content = nodes.definition()
    type_item_content += make_python_xref_nodes(
        field_type,
        state,
        hide_namespace=True)
    type_item.append(type_item_content)
    return type_item


def create_default_target_item_node(field, state):
    """Create a definition list item node that describes the default target
    of a ConfigurableField config.

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
    target_type = '.'.join((field.target.__module__,
                            field.target.__name__))
    default_item_content = nodes.definition()
    default_item_content += make_python_xref_nodes(target_type, state)
    default_item.append(default_item_content)
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
}
