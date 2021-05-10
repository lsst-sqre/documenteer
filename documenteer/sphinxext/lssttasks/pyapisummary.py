"""Sphinx extensions for summarizing the Python API for tasks.
"""

__all__ = ("TaskApiDirective",)

from docutils import nodes
from docutils.parsers.rst import Directive
from sphinx.addnodes import (
    desc,
    desc_addname,
    desc_annotation,
    desc_content,
    desc_signature,
    seealso,
)
from sphinx.domains.python import PyXRefRole, _pseudo_parse_arglist
from sphinx.errors import SphinxError
from sphinx.util.inspect import signature as make_signature
from sphinx.util.inspect import stringify_signature
from sphinx.util.logging import getLogger

from .taskutils import extract_docstring_summary, get_docstring, get_type


class TaskApiDirective(Directive):
    """``lsst-task-api-summary`` directive that renders a summary of a LSST
    Science Pipelines Task's Python API and links to the regular Python API
    documentation from ``automodapi``.
    """

    directive_name = "lsst-task-api-summary"
    """Default name of this directive."""

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
                "{} directive requires a Task class "
                "name as an argument".format(self.directive_name)
            )

        logger.debug(
            "%s running with %r", self.directive_name, task_class_name
        )

        task_class = get_type(task_class_name)

        new_nodes = []
        new_nodes.extend(self._format_import_example(task_class))
        new_nodes.extend(self._format_summary_node(task_class))
        new_nodes.extend(self._format_api_docs_link_message(task_class))

        return new_nodes

    def _format_summary_node(self, task_class):
        """Format a section node with a summary of a Task class's key APIs."""
        modulename = task_class.__module__
        classname = task_class.__name__
        nodes = []

        nodes.append(self._format_class_nodes(task_class))

        nodes.append(self._format_config_nodes(modulename, classname))

        methods = ("run", "runDataRef")
        for method in methods:
            if hasattr(task_class, method):
                method_obj = getattr(task_class, method)
                nodes.append(
                    self._format_method_nodes(
                        method_obj, modulename, classname
                    )
                )
        return nodes

    def _format_class_nodes(self, task_class):
        """Create a ``desc`` node summarizing the class docstring."""
        # Patterned after PyObject.handle_signature in Sphinx.
        # https://github.com/sphinx-doc/sphinx/blob/3e57ea0a5253ac198c1bff16c40abe71951bb586/sphinx/domains/python.py#L246

        modulename = task_class.__module__
        classname = task_class.__name__
        fullname = ".".join((modulename, classname))

        # The signature term
        signature = make_signature(task_class, bound_method=False)
        desc_sig_node = self._format_signature(
            signature, modulename, classname, fullname, "py:class"
        )

        # The content is the one-sentence summary.
        content_node = desc_content()
        content_node += self._create_doc_summary(
            task_class, fullname, "py:class"
        )

        desc_node = desc()
        desc_node["noindex"] = True
        desc_node["domain"] = "py"
        desc_node["objtype"] = "class"
        desc_node += desc_sig_node
        desc_node += content_node
        return desc_node

    def _format_method_nodes(self, task_method, modulename, classname):
        """Create a ``desc`` node summarizing a method docstring."""
        methodname = task_method.__name__
        fullname = ".".join((modulename, classname, methodname))

        # The signature term
        signature = make_signature(task_method, bound_method=True)
        desc_sig_node = self._format_signature(
            signature, modulename, classname, fullname, "py:meth"
        )

        # The content is the one-sentence summary.
        content_node = desc_content()
        content_node += self._create_doc_summary(
            task_method, fullname, "py:meth"
        )

        desc_node = desc()
        desc_node["noindex"] = True
        desc_node["domain"] = "py"
        desc_node["objtype"] = "method"
        desc_node += desc_sig_node
        desc_node += content_node
        return desc_node

    def _format_signature(
        self, signature, modulename, classname, fullname, refrole
    ):
        xref = PyXRefRole()

        arglist = (
            stringify_signature(
                signature, show_annotation=False, show_return_annotation=False
            )
            .lstrip("(")
            .rstrip(")")
        )

        desc_sig_node = desc_signature()
        desc_sig_node["module"] = modulename
        desc_sig_node["class"] = classname
        desc_sig_node["fullname"] = fullname

        # Prefix the API signature with the API type
        prefix = None
        if refrole == "py:class":
            prefix = "class"
        elif refrole == "py:meth":
            prefix = "method"
        elif refrole == "py:attr":
            prefix = "attribute"
        if prefix:
            desc_sig_node += desc_annotation(prefix, prefix)

        # The API name is linked to the canonical API docs
        name_xref_nodes, _ = xref(
            refrole,
            "~" + fullname,
            "~" + fullname,
            self.lineno,
            self.state.inliner,
        )
        desc_sig_name_node = desc_addname()
        desc_sig_name_node += name_xref_nodes
        desc_sig_node += desc_sig_name_node
        if refrole in ("py:class", "py:meth"):
            _pseudo_parse_arglist(desc_sig_node, arglist)

        return desc_sig_node

    def _create_doc_summary(self, obj, fullname, refrole):
        """Create a paragraph containing the object's one-sentence docstring
        summary with a link to further documentation.

        The paragrah should be inserted into the ``desc`` node's
        ``desc_content``.
        """
        summary_text = extract_docstring_summary(get_docstring(obj))
        summary_text = summary_text.strip()
        # Strip the last "." because the linked ellipses take its place
        if summary_text.endswith("."):
            summary_text = summary_text.rstrip(".")
        content_node_p = nodes.paragraph(text=summary_text)
        content_node_p += self._create_api_details_link(fullname, refrole)
        return content_node_p

    def _create_api_details_link(self, fullname, refrole):
        """Appends a link to the API docs, labelled as "...", that is appended
        to the content paragraph of an API description.

        This affordance indicates that more documentation is available, and
        that by clicking on the ellipsis the user can find that documentation.
        """
        ref_text = "... <{}>".format(fullname)
        xref = PyXRefRole()
        xref_nodes, _ = xref(
            refrole, ref_text, ref_text, self.lineno, self.state.inliner
        )
        return xref_nodes

    def _format_config_nodes(self, modulename, classname):
        """Create a ``desc`` node summarizing the config attribute

        The ``config`` attribute is not statically available from a task class.
        This method manually creates a signature and docstring for the
        config attribute.
        """
        fullname = "{0}.{1}.config".format(modulename, classname)

        # The signature term
        desc_sig_node = desc_signature()
        desc_sig_node["module"] = modulename
        desc_sig_node["class"] = classname
        desc_sig_node["fullname"] = fullname

        prefix = "attribute"
        desc_sig_node += desc_annotation(prefix, prefix)
        desc_sig_name_node = desc_addname("config", "config")
        # Fakes the look of a cross reference.
        desc_sig_name_node["classes"].extend(["xref", "py"])
        desc_sig_node += desc_sig_name_node

        # The content is the one-sentence summary.
        summary_text = "Access configuration fields and retargetable subtasks."
        content_node_p = nodes.paragraph(text=summary_text)
        content_node = desc_content()
        content_node += content_node_p

        desc_node = desc()
        desc_node["noindex"] = True
        desc_node["domain"] = "py"
        desc_node["objtype"] = "attribute"
        desc_node += desc_sig_node
        desc_node += content_node
        return desc_node

    def _format_import_example(self, task_class):
        """Generate nodes that show a code sample demonstrating how to import
        the task class.

        Parameters
        ----------
        task_class : ``lsst.pipe.base.Task``-type
            The Task class.

        Returns
        -------
        nodes : `list` of docutils nodes
            Docutils nodes showing a class import statement.
        """
        code = "from {0.__module__} import {0.__name__}".format(task_class)

        # This is a bare-bones version of what Sphinx's code-block directive
        # does. The 'language' attr triggers the pygments treatment.
        literal_node = nodes.literal_block(code, code)
        literal_node["language"] = "py"

        return [literal_node]

    def _format_api_docs_link_message(self, task_class):
        """Format a message referring the reader to the full API docs.

        Parameters
        ----------
        task_class : ``lsst.pipe.base.Task``-type
            The Task class.

        Returns
        -------
        nodes : `list` of docutils nodes
            Docutils nodes showing a link to the full API docs.
        """
        fullname = "{0.__module__}.{0.__name__}".format(task_class)

        p_node = nodes.paragraph()

        _ = "See the "
        p_node += nodes.Text(_, _)

        xref = PyXRefRole()
        xref_nodes, _ = xref(
            "py:class",
            "~" + fullname,
            "~" + fullname,
            self.lineno,
            self.state.inliner,
        )

        p_node += xref_nodes

        _ = " API reference for complete details."
        p_node += nodes.Text(_, _)

        seealso_node = seealso()
        seealso_node += p_node

        return [seealso_node]
