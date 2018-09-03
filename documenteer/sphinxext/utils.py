"""Utilities for making Sphinx extensions.
"""

__all__ = ('parse_rst_content', 'make_python_xref_nodes', 'make_section')

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
        viewlist.append(line, source='', offset=i)

    with switch_source_input(state, viewlist):
        state.nested_parse(viewlist, 0, container_node)

    return container_node.children


def make_python_xref_nodes(py_obj, state, hide_namespace=False):
    """Make docutils nodes containing a cross-reference to a Python object.

    Parameters
    ----------
    py_obj : `str`
        Name of the Python object. For example `mypackage.mymodule.MyClass`.
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

       make_python_xref_nodes('numpy.sin', self.state)
    """
    if hide_namespace:
        template = ':py:obj:`~{}`\n'
    else:
        template = ':py:obj:`{}`\n'
    xref_text = template.format(py_obj)

    return parse_rst_content(xref_text, state)


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
    section['ids'].append(nodes.make_id(section_id))
    section['names'].append(section_id)
    if contents is not None:
        section.extend(contents)
    return section