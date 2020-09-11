"""Directives that list and create toctrees of task framework topics.
"""

__all__ = (
    "TaskListDirective",
    "CmdLineTaskListDirective",
    "PipelineTaskListDirective",
    "ConfigurableListDirective",
    "ConfigListDirective",
    "task_topic_list",
    "process_task_topic_list",
)

import posixpath

import sphinx.addnodes
from docutils import nodes
from docutils.parsers.rst import Directive, directives
from sphinx.util.logging import getLogger


class BaseTopicListDirective(Directive):
    """Base class for directives that lists task topics."""

    _logger = getLogger(__name__)

    required_arguments = 0
    optional_arguments = 0
    has_content = False
    option_spec = {
        "root": directives.unchanged,
        "toctree": directives.unchanged,
    }

    @property
    def types(self):
        """The set of types that this directive lists.

        "Types" themselves are strings:

        - ``'Task'``
        - ``'PipelineTask'``
        - ``'CmdLineTask'``
        - ``'Configurable'``
        - ``'Config'``

        These names correspond to the ``'types'`` key of the
        ``lsst_task_topics`` environment attribute set by the
        topic marker directives (such as
        `documenteer.sphinxext.lssttasks.topics.TaskTopicDirective`).
        """
        raise NotImplementedError

    def run(self):
        """Main entrypoint method.

        Returns
        -------
        new_nodes : `list`
            Nodes to add to the doctree.
        """
        self._env = self.state.document.settings.env

        nodes = []

        if "toctree" in self.options:
            # Insert a hidden toctree
            toctree_node = self._build_toctree()
            nodes.append(toctree_node)

        # Placeholder node rendered in `process_task_topic_list`
        list_node = task_topic_list()
        list_node["types"] = self.types
        list_node["root_namespace"] = self.options["root"]
        nodes.append(list_node)

        return nodes

    def _build_toctree(self):
        """Create a hidden toctree node with the contents of a directory
        prefixed by the directory name specified by the `toctree` directive
        option.
        """
        dirname = posixpath.dirname(self._env.docname)
        tree_prefix = self.options["toctree"].strip()
        root = posixpath.normpath(posixpath.join(dirname, tree_prefix))
        docnames = [
            docname
            for docname in self._env.found_docs
            if docname.startswith(root)
        ]

        # Sort docnames alphabetically based on **class** name.
        # The standard we assume is that task doc pages are named after
        # their Python namespace.
        # NOTE: this ordering only applies to the toctree; the visual ordering
        # is set by `process_task_topic_list`.
        # NOTE: docnames are **always** POSIX-like paths
        class_names = [
            docname.split("/")[-1].split(".")[-1] for docname in docnames
        ]
        docnames = [
            docname
            for docname, _ in sorted(
                zip(docnames, class_names), key=lambda pair: pair[1]
            )
        ]

        tocnode = sphinx.addnodes.toctree()
        tocnode["includefiles"] = docnames
        tocnode["entries"] = [(None, docname) for docname in docnames]
        tocnode["maxdepth"] = -1
        tocnode["glob"] = None
        tocnode["hidden"] = True

        return tocnode


class TaskListDirective(BaseTopicListDirective):
    """``lsst-tasks`` directive that creates a toctree of LSST task topics
    (specifically subclasses of ``lsst.pipe.base.Task``, but not including
    subclasses of ``lsst.pipe.base.CmdLineTask`` or
    ``lsst.pipe.base.PipelineTask``).
    """

    directive_name = "lsst-tasks"
    """Default name of this directive.
    """

    @property
    def types(self):
        return set(("Task",))


class CmdLineTaskListDirective(BaseTopicListDirective):
    """``lsst-tasks`` directive that creates a toctree of LSST command-line
    tasks (``lsst.pipe.base.CmdLineTask``).
    """

    directive_name = "lsst-cmdlinetasks"
    """Default name of this directive.
    """

    @property
    def types(self):
        return set(("CmdLineTask",))


class PipelineTaskListDirective(BaseTopicListDirective):
    """``lsst-tasks`` directive that creates a toctree of LSST pipeline
    tasks (``lsst.pipe.base.PipelineTask``).
    """

    directive_name = "lsst-pipelinetasks"
    """Default name of this directive.
    """

    @property
    def types(self):
        return set(("PipelineTask",))


class ConfigurableListDirective(BaseTopicListDirective):

    directive_name = "lsst-configurables"

    @property
    def types(self):
        return set(("Configurable",))


class ConfigListDirective(TaskListDirective):

    directive_name = "lsst-configs"

    @property
    def types(self):
        return set(("Config",))


class task_topic_list(nodes.comment):
    """Placeholder node for a task topic listing.

    This node is processed by `process_task_topic_list`.
    """


def process_task_topic_list(app, doctree, fromdocname):
    """Process the ``task_topic_list`` node to generate a rendered listing of
    Task, Configurable, or Config topics (as determined by the types
    key of the ``task_topic_list`` node).

    This is called during the "doctree-resolved" phase so that the
    ``lsst_task_topcs`` environment attribute is fully set.
    """
    logger = getLogger(__name__)
    logger.debug("Started process_task_list")

    env = app.builder.env

    for node in doctree.traverse(task_topic_list):
        try:
            topics = env.lsst_task_topics
        except AttributeError:
            message = (
                "Environment does not have 'lsst_task_topics', "
                "can't process the listing."
            )
            logger.warning(message)
            node.replace_self(nodes.paragraph(text=message))
            continue

        root = node["root_namespace"]

        # Sort tasks by the topic's class name.
        # NOTE: if the presentation of the link is changed to the fully
        # qualified name, with full Python namespace, then the topic_names
        # should be changed to match that.
        topic_keys = [
            k
            for k, topic in topics.items()
            if topic["type"] in node["types"]
            if topic["fully_qualified_name"].startswith(root)
        ]
        topic_names = [
            topics[k]["fully_qualified_name"].split(".")[-1]
            for k in topic_keys
        ]
        topic_keys = [
            k
            for k, _ in sorted(
                zip(topic_keys, topic_names), key=lambda pair: pair[1]
            )
        ]

        if len(topic_keys) == 0:
            # Fallback if no topics are found
            p = nodes.paragraph(text="No topics.")
            node.replace_self(p)
            continue

        dl = nodes.definition_list()
        for key in topic_keys:
            topic = topics[key]
            class_name = topic["fully_qualified_name"].split(".")[-1]
            summary_text = topic["summary_node"][0].astext()

            # Each topic in the listing is a definition list item. The term is
            # the linked class name and the description is the summary
            # sentence from the docstring _or_ the content of the
            # topic directive
            dl_item = nodes.definition_list_item()

            # Can insert an actual reference since the doctree is resolved.
            ref_node = nodes.reference("", "")
            ref_node["refdocname"] = topic["docname"]
            ref_node["refuri"] = app.builder.get_relative_uri(
                fromdocname, topic["docname"]
            )
            # NOTE: Not appending an anchor to the URI because task topics
            # are designed to occupy an entire page.
            link_label = nodes.Text(class_name, class_name)
            ref_node += link_label

            term = nodes.term()
            term += ref_node
            dl_item += term

            # We're degrading the summary to plain text to avoid syntax issues
            # and also because it may be distracting
            def_node = nodes.definition()
            def_node += nodes.paragraph(text=summary_text)
            dl_item += def_node
            dl += dl_item

        # Replace the task_list node (a placeholder) with this renderable
        # content
        node.replace_self(dl)
