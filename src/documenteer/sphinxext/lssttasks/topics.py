"""Directives that mark task and configurable topics for the LSST Science
Pipelines documentation.
"""

__all__ = (
    "ConfigurableTopicDirective",
    "TaskTopicDirective",
    "ConfigTopicDirective",
)

from docutils import nodes
from docutils.parsers.rst import Directive
from sphinx.errors import SphinxError
from sphinx.util.docutils import switch_source_input
from sphinx.util.logging import getLogger

from ..utils import parse_rst_content
from .crossrefs import format_config_id, format_task_id
from .taskutils import extract_docstring_summary, get_docstring, get_type


class BaseTopicDirective(Directive):
    """Base for topic target directives."""

    _logger = getLogger(__name__)

    has_content = True
    required_arguments = 1

    @property
    def directive_name(self):
        raise NotImplementedError

    def get_type(self, class_name):
        """Get the topic type."""
        raise NotImplementedError

    def get_target_id(self, class_name):
        """Get the reference ID for this topic directive."""
        raise NotImplementedError

    def run(self):
        """Main entrypoint method.

        Returns
        -------
        new_nodes : `list`
            Nodes to add to the doctree.
        """
        env = self.state.document.settings.env

        try:
            class_name = self.arguments[0]
        except IndexError:
            raise SphinxError(
                "{0} directive requires a class name as an "
                "argument".format(self.directive_name)
            )
        self._logger.debug(
            "%s using class %s", self.directive_name, class_name
        )

        summary_node = self._create_summary_node(class_name)

        # target_id = format_task_id(class_name)
        target_id = self.get_target_id(class_name)
        target_node = nodes.target("", "", ids=[target_id])

        # Store these task/configurable topic nodes in the environment for
        # later cross referencing.
        if not hasattr(env, "lsst_task_topics"):
            env.lsst_task_topics = {}
        env.lsst_task_topics[target_id] = {
            "docname": env.docname,
            "lineno": self.lineno,
            "target": target_node,
            "summary_node": summary_node,
            "fully_qualified_name": class_name,
            "type": self.get_type(class_name),
        }

        return [target_node]

    def _create_summary_node(self, class_name):
        if len(self.content) > 0:
            # Try to get the summary content from the directive content
            container_node = nodes.container()
            container_node.document = self.state.document
            content_view = self.content
            with switch_source_input(self.state, content_view):
                self.state.nested_parse(content_view, 0, container_node)
            return container_node.children

        else:
            # Fallback is to get summary sentence from class docstring.
            return self._get_docstring_summary(class_name)

    def _get_docstring_summary(self, class_name):
        obj = get_type(class_name)
        summary_text = extract_docstring_summary(get_docstring(obj))
        if summary_text == "":
            summary_text = "No description available."
        summary_text = summary_text.strip() + "\n"
        return parse_rst_content(summary_text, self.state)


class ConfigurableTopicDirective(BaseTopicDirective):
    """``lsst-configurable-topic`` directive that labels a Configurable's topic
    page.

    Configurables are essentially generalized tasks. They have a ConfigClass,
    but don't have run methods.
    """

    directive_name = "lsst-configurable-topic"
    """Default name of this directive.
    """

    def get_type(self, class_name):
        return "Configurable"

    def get_target_id(self, class_name):
        return format_task_id(class_name)


class TaskTopicDirective(BaseTopicDirective):
    """``lsst-task-topic`` directive that labels a Task's topic page."""

    directive_name = "lsst-task-topic"
    """Default name of this directive.
    """

    def get_type(self, class_name):
        try:
            from lsst.pipe.base import CmdLineTask
        except ImportError:
            CmdLineTask = None
        try:
            from lsst.pipe.base import PipelineTask
        except ImportError:
            PipelineTask = None

        obj = get_type(class_name)
        if PipelineTask is not None and issubclass(obj, PipelineTask):
            return "PipelineTask"
        elif CmdLineTask is not None and issubclass(obj, CmdLineTask):
            return "CmdLineTask"
        else:
            return "Task"

    def get_target_id(self, class_name):
        return format_task_id(class_name)


class ConfigTopicDirective(BaseTopicDirective):
    """``lsst-config-topic`` directive that labels a Config topic page.

    Configs are lsst.pex.config.config.Config subclasses.
    """

    directive_name = "lsst-config-topic"
    """Default name of this directive.
    """

    def get_type(self, class_name):
        return "Config"

    def get_target_id(self, class_name):
        return format_config_id(class_name)
