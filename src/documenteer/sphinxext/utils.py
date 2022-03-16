"""Utilities for making Sphinx extensions.
"""

__all__ = (
    "parse_rst_content",
    "make_python_xref_nodes",
    "make_python_xref_nodes_for_type",
    "make_section",
)

import re

from docutils import nodes
from docutils.statemachine import ViewList
from sphinx.util.docutils import switch_source_input


def parse_rst_content(content, state):
    """Parse rST-formatted string content into docutils nodes

    Parameters
    ----------
    content : `str`
        ReStructuredText-formatted content
    state : ``docutils.statemachine.State``
        Usually the directive's ``state`` attribute.

    Returns
    -------
    instance from ``docutils.nodes``
        Docutils node representing the ``content``.
    """
    # http://www.sphinx-doc.org/en/master/extdev/markupapi.html
    # #parsing-directive-content-as-rest
    container_node = nodes.section()
    container_node.document = state.document

    viewlist = ViewList()
    for i, line in enumerate(content.splitlines()):
        viewlist.append(line, source="", offset=i)

    with switch_source_input(state, viewlist):
        state.nested_parse(viewlist, 0, container_node)

    return container_node.children


def make_python_xref_nodes(py_typestr, state, hide_namespace=False):
    """Make docutils nodes containing a cross-reference to a Python object.

    Parameters
    ----------
    py_typestr : `str`
        Name of the Python object. For example
        ``'mypackage.mymodule.MyClass'``. If you have the object itself, or
        its type, use the `make_python_xref_nodes_for_type` function instead.
    state : ``docutils.statemachine.State``
        Usually the directive's ``state`` attribute.
    hide_namespace : `bool`, optional
        If `True`, the namespace of the object is hidden in the rendered
        cross reference. Internally, this uses ``:py:obj:`~{py_obj}` (note
        tilde).

    Returns
    -------
    instance from ``docutils.nodes``
        Docutils node representing the cross reference.

    Examples
    --------
    If called from within a directive:

    .. code-block:: python

       make_python_xref_nodes("numpy.sin", self.state)

    See also
    --------
    `make_python_xref_nodes_for_type`
    """
    if hide_namespace:
        template = ":py:obj:`~{}`\n"
    else:
        template = ":py:obj:`{}`\n"
    xref_text = template.format(py_typestr)

    return parse_rst_content(xref_text, state)


def make_python_xref_nodes_for_type(py_type, state, hide_namespace=False):
    """Make docutils nodes containing a cross-reference to a Python object,
    given the object's type.

    Parameters
    ----------
    py_type : `obj`
        Type of an object. For example ``mypackage.mymodule.MyClass``. If you
        have instance of the type, use ``type(myinstance)``.
    state : ``docutils.statemachine.State``
        Usually the directive's ``state`` attribute.
    hide_namespace : `bool`, optional
        If `True`, the namespace of the object is hidden in the rendered
        cross reference. Internally, this uses ``:py:obj:`~{py_obj}` (note
        tilde).

    Returns
    -------
    instance from ``docutils.nodes``
        Docutils node representing the cross reference.

    Examples
    --------
    If called from within a directive:

    .. code-block:: python

       make_python_xref_nodes(numpy.sin, self.state)

    See also
    --------
    `make_python_xref_nodes`
    """
    if py_type.__module__ == "builtins":
        typestr = py_type.__name__
    else:
        typestr = ".".join((py_type.__module__, py_type.__name__))
    return make_python_xref_nodes(
        typestr, state, hide_namespace=hide_namespace
    )


def make_section(section_id=None, contents=None):
    """Make a docutils section node.

    Parameters
    ----------
    section_id : `str`
        Section identifier, which is appended to both the ``ids`` and ``names``
        attributes.
    contents : `list` of ``docutils.nodes``
        List of docutils nodes that are inserted into the section.

    Returns
    -------
    ``docutils.nodes.section``
        Docutils section node.
    """
    section = nodes.section()
    section["ids"].append(nodes.make_id(section_id))
    section["names"].append(section_id)
    if contents is not None:
        section.extend(contents)
    return section


ROLE_DISPLAY_PATTERN = re.compile(r"(?P<display>.+)<(?P<reference>.+)>")


def split_role_content(role_rawsource):
    """Split the ``rawsource`` of a role into standard components.

    Parameters
    ----------
    role_rawsource : `str`
        The content of the role: its ``rawsource`` attribute.

    Returns
    -------
    parts : `dict`
        Dictionary with keys:

        ``last_component`` (`bool`)
           If `True`, the display should show only the last component of a
           namespace. The user signals this by prefixing the role's content
           with a ``~`` character.

        ``display`` (`str`)
           Custom display content. See Examples.

        ``ref`` (`str`)
           The reference content. If the role doesn't have a custom display,
           the reference will be the role's content. The ``ref`` never
           includes a ``~`` prefix.

    Examples
    --------
    >>> split_role_role('Tables <lsst.afw.table.Table>')
    {'last_component': False, 'display': 'Tables',
    'ref': 'lsst.afw.table.Table'}

    >>> split_role_role('~lsst.afw.table.Table')
    {'last_component': True, 'display': None, 'ref': 'lsst.afw.table.Table'}
    """
    parts = {"last_component": False, "display": None, "ref": None}

    if role_rawsource.startswith("~"):
        # Only the last part of a namespace should be shown.
        parts["last_component"] = True
        # Strip that marker off
        role_rawsource = role_rawsource.lstrip("~")

    match = ROLE_DISPLAY_PATTERN.match(role_rawsource)
    if match:
        parts["display"] = match.group("display").strip()
        parts["ref"] = match.group("reference").strip()
    else:
        # No suggested display
        parts["display"] = None
        parts["ref"] = role_rawsource.strip()

    return parts
