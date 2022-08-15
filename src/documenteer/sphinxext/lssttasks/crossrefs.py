"""Targets and reference roles for LSST Task objects.
"""

__all__ = (
    "format_task_id",
    "format_config_id",
    "format_configfield_id",
    "pending_task_xref",
    "task_ref_role",
    "config_ref_role",
    "configfield_ref_role",
    "process_pending_task_xref_nodes",
    "process_pending_config_xref_nodes",
    "process_pending_configfield_xref_nodes",
)

from docutils import nodes
from sphinx.util.logging import getLogger

from ..utils import split_role_content


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
    return nodes.make_id("lsst-task-{}".format(task_class_name))


def format_config_id(config_class_name):
    """Format the ID of a standalone config topic reference node.

    Parameters
    ----------
    config_class_name : `str`
        Importable name of the config class. For example,
        ``'lsst.pipe.tasks.processCcd.ProcessCcdConfig'``.

    Returns
    -------
    node_id : `str`
        Node ID for the config topic reference node.
    """
    return nodes.make_id("lsst-config-{}".format(config_class_name))


def format_configfield_id(config_class_name, field_name):
    """Format the ID of a configuration field topic.

    Parameters
    ----------
    config_class_name : `str`
        Importable name of the config class. For example,
        ``'lsst.pipe.tasks.processCcd.ProcessCcdConfig'``.
    field_name : `str`
        Name of the configuration field attribute.

    Returns
    -------
    node_id : `str`
        Node ID for the config topic reference node.
    """
    return nodes.make_id(
        "lsst-configfield-{0}-{1}".format(config_class_name, field_name)
    )


class pending_task_xref(nodes.Inline, nodes.Element):
    """Node for task cross-references that cannot be resolved without complete
    information about all documents.
    """


class pending_config_xref(nodes.Inline, nodes.Element):
    """Node for config cross-references (to ``lsst-config`` directives) that
    cannot be resolved without complete information about all documents.
    """


class pending_configfield_xref(nodes.Inline, nodes.Element):
    """Node for cross-references to configuration field nodes that
    cannot be resolved without complete information about all documents.
    """


def task_ref_role(
    name, rawtext, text, lineno, inliner, options=None, content=None
):
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
    event to insert links to the locations of ``lsst-task-topic`` directives.
    """
    logger = getLogger(__name__)
    env = app.builder.env

    for node in doctree.traverse(pending_task_xref):
        content = []

        # The source of the node is the class name the user entered via the
        # lsst-task-topic role. For example:
        # lsst.pipe.tasks.processCcd.ProcessCcdTask
        role_parts = split_role_content(node.rawsource)
        task_id = format_task_id(role_parts["ref"])
        if role_parts["display"]:
            # user's custom display text
            display_text = role_parts["display"]
        elif role_parts["last_component"]:
            # just the name of the class
            display_text = role_parts["ref"].split(".")[-1]
        else:
            display_text = role_parts["ref"]
        link_label = nodes.literal()
        link_label += nodes.Text(display_text, display_text)

        if (
            hasattr(env, "lsst_task_topics")
            and task_id in env.lsst_task_topics
        ):
            # A task topic, marked up with the lsst-task-topic directive is
            # available
            task_data = env.lsst_task_topics[task_id]

            ref_node = nodes.reference("", "")
            ref_node["refdocname"] = task_data["docname"]
            ref_node["refuri"] = app.builder.get_relative_uri(
                fromdocname, task_data["docname"]
            )
            ref_node["refuri"] += "#" + task_data["target"]["refid"]

            ref_node += link_label

            content.append(ref_node)

        else:
            # Fallback if the task topic isn't known. Just print the label text
            content.append(link_label)

            message = "lsst-task could not find a reference to %s"
            logger.warning(message, role_parts["ref"], location=node)

        # replacing the pending_task_xref node with this reference
        node.replace_self(content)


def config_ref_role(
    name, rawtext, text, lineno, inliner, options=None, content=None
):
    """Process a role that references the target nodes created by the
    ``lsst-config-topic`` directive.

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

    See also
    --------
    `format_config_id`
    `ConfigTopicTargetDirective`
    `pending_config_xref`
    """
    node = pending_config_xref(rawsource=text)
    return [node], []


def process_pending_config_xref_nodes(app, doctree, fromdocname):
    """Process the ``pending_config_xref`` nodes during the
    ``doctree-resolved`` event to insert links to the locations of
    ``lsst-config-topic`` directives.

    See also
    --------
    `config_ref_role`
    `ConfigTopicTargetDirective`
    `pending_config_xref`
    """
    logger = getLogger(__name__)
    env = app.builder.env

    for node in doctree.traverse(pending_config_xref):
        content = []

        # The source of the node is the content the authored entered in the
        # lsst-config role
        role_parts = split_role_content(node.rawsource)
        config_id = format_config_id(role_parts["ref"])
        if role_parts["display"]:
            # user's custom display text
            display_text = role_parts["display"]
        elif role_parts["last_component"]:
            # just the name of the class
            display_text = role_parts["ref"].split(".")[-1]
        else:
            display_text = role_parts["ref"]
        link_label = nodes.literal()
        link_label += nodes.Text(display_text, display_text)

        if (
            hasattr(env, "lsst_task_topics")
            and config_id in env.lsst_task_topics
        ):
            # A config topic, marked up with the lsst-task directive is
            # available
            config_data = env.lsst_task_topics[config_id]

            ref_node = nodes.reference("", "")
            ref_node["refdocname"] = config_data["docname"]
            ref_node["refuri"] = app.builder.get_relative_uri(
                fromdocname, config_data["docname"]
            )
            ref_node["refuri"] += "#" + config_data["target"]["refid"]

            ref_node += link_label

            content.append(ref_node)

        else:
            # Fallback if the config topic isn't known. Just print the
            # role's formatted content.
            content.append(link_label)

            message = "lsst-config could not find a reference to %s"
            logger.warning(message, role_parts["ref"], location=node)

        # replacing the pending_config_xref node with this reference
        node.replace_self(content)


def configfield_ref_role(
    name, rawtext, text, lineno, inliner, options=None, content=None
):
    """Process a role that references the Task configuration field nodes
    created by the ``lsst-config-fields``, ``lsst-task-config-subtasks``,
    and ``lsst-task-config-subtasks`` directives.

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

    See also
    --------
    `format_configfield_id`
    `pending_configfield_xref`
    `process_pending_configfield_xref_nodes`
    """
    node = pending_configfield_xref(rawsource=text)
    return [node], []


def process_pending_configfield_xref_nodes(app, doctree, fromdocname):
    """Process the ``pending_configfield_xref`` nodes during the
    ``doctree-resolved`` event to insert links to the locations of
    configuration field nodes.

    See also
    --------
    `format_configfield_id`
    `configfield_ref_role`
    `pending_configfield_xref`
    """
    logger = getLogger(__name__)
    env = app.builder.env

    for node in doctree.traverse(pending_configfield_xref):
        content = []

        # The source is the text the user entered into the role, which is
        # the importable name of the config class's and the attribute
        role_parts = split_role_content(node.rawsource)
        namespace_components = role_parts["ref"].split(".")
        field_name = namespace_components[-1]
        class_namespace = namespace_components[:-1]
        configfield_id = format_configfield_id(class_namespace, field_name)
        if role_parts["display"]:
            # user's custom display text
            display_text = role_parts["display"]
        elif role_parts["last_component"]:
            # just the name of the class
            display_text = role_parts["ref"].split(".")[-1]
        else:
            display_text = role_parts["ref"]
        link_label = nodes.literal()
        link_label += nodes.Text(display_text, display_text)

        if (
            hasattr(env, "lsst_configfields")
            and configfield_id in env.lsst_configfields
        ):
            # A config field topic is available
            configfield_data = env.lsst_configfields[configfield_id]

            ref_node = nodes.reference("", "")
            ref_node["refdocname"] = configfield_data["docname"]
            ref_node["refuri"] = app.builder.get_relative_uri(
                fromdocname, configfield_data["docname"]
            )
            ref_node["refuri"] += "#" + configfield_id

            ref_node += link_label

            content.append(ref_node)

        else:
            # Fallback if the config field isn't known. Just print the Config
            # field attribute name
            literal_node = nodes.literal()
            link_label = nodes.Text(field_name, field_name)
            literal_node += link_label

            content.append(literal_node)

            message = "lsst-config-field could not find a reference to %s"
            logger.warning(message, role_parts["ref"], location=node)

        # replacing the pending_configfield_xref node with this reference
        node.replace_self(content)
