"""Targets and reference roles for LSST Task objects.
"""

__all__ = ('format_task_id', 'TaskTopicTargetDirective',
           'pending_task_xref', 'task_ref_role',
           'process_pending_task_xref_nodes')

from docutils import nodes
from docutils.parsers.rst import Directive
from sphinx.util.logging import getLogger
from sphinx.errors import SphinxError


def format_task_id(task_class_name):
    """Format the ID of a task topic reference node.

    Parameters
    ----------
    task_class_name : `str`
        Importable name of the task class. For example,
        ``'lsst.pipe.tasks.processCcd.ProcessCcdTask'``.

    Returns
    -------
    task_id : `str`
        Node ID for the task topic reference node.
    """
    return nodes.make_id('lsst-task-{}'.format(task_class_name))


class TaskTopicTargetDirective(Directive):
    """``lsst-task`` directive that labels a Task's topic page.
    """

    directive_name = 'lsst-task'
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
        env = self.state.document.settings.env
        logger = getLogger(__name__)

        try:
            task_class_name = self.arguments[0]
        except IndexError:
            raise SphinxError(
                '{} directive requires a Task class name as an '
                'argument'.format(self.directive_name)
            )
        logger.debug('%s using Task class %s',
                     self.directive_name, task_class_name)

        target_id = format_task_id(task_class_name)
        target_node = nodes.target('', '', ids=[target_id])

        # Store these task topic nodes in the environment for later cross
        # referencing.
        if not hasattr(env, 'lsst_tasks'):
            env.lsst_tasks = {}
        env.lsst_tasks[target_id] = {
            'docname': env.docname,
            'lineno': self.lineno,
            'target': target_node,
        }

        return [target_node]


class pending_task_xref(nodes.Inline, nodes.Element):
    """Node for task cross-references that cannot be resolved without complete
    information about all documents.
    """


def task_ref_role(name, rawtext, text, lineno, inliner,
                  options=None, content=None):
    """Process a role that references the target nodes created by the
    ``lsst-task`` directive.

    Parameters
    ----------
    name
        The role name used in the document.
    rawtext
        The entire markup snippet, with role.
    text
        The text marked with the role.
    lineno
        The line number where ``rawtext`` appears in the input.
    inliner
        The inliner instance that called us.
    options
        Directive options for customization.
    content
        The directive content for customization.

    Returns
    -------
    nodes : `list`
        List of nodes to insert into the document.
    messages : `list`
        List of system messages.
    """
    # app = inliner.document.settings.env.app
    node = pending_task_xref(rawsource=text)
    return [node], []


def process_pending_task_xref_nodes(app, doctree, fromdocname):
    """Process the ``pending_task_xref`` nodes during the ``doctree-resolved``
    event to insert links to the locations of ``lsst-task`` directives.
    """
    logger = getLogger(__name__)
    env = app.builder.env

    for node in doctree.traverse(pending_task_xref):
        content = []

        # The source of the node is the class name the user entered via the
        # lsst-task role. For example:
        # lsst.pipe.tasks.processCcd.ProcessCcdTask
        text = node.rawsource
        task_id = format_task_id(text)
        class_name = text.split('.')[-1]  # just the name of the class

        if hasattr(env, 'lsst_tasks') and task_id in env.lsst_tasks:
            # A task topic, marked up with the lsst-task directive is available
            task_data = env.lsst_tasks[task_id]

            ref_node = nodes.reference('', '')
            ref_node['refdocname'] = task_data['docname']
            ref_node['refuri'] = app.builder.get_relative_uri(
                fromdocname, task_data['docname'])
            ref_node['refuri'] += '#' + task_data['target']['refid']

            link_label = nodes.Text(class_name, class_name)
            literal_node = nodes.literal()
            literal_node += link_label
            ref_node += literal_node

            content.append(ref_node)

        else:
            # Fallback if the task topic isn't known. Just print the task class
            # name.
            literal_node = nodes.literal()
            link_label = nodes.Text(class_name, class_name)
            literal_node += link_label

            content.append(literal_node)

            message = 'lsst-task could not find a reference to %s'
            logger.warning(message, text, location=node)

        # replacing the pending_task_xref node with this reference
        node.replace_self(content)
