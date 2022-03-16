"""Sphinx extensions for documenting LSST Science Pipelines Tasks.
"""

__all__ = ["setup"]

from documenteer.version import __version__

from .configfieldlists import (
    ConfigFieldListingDirective,
    StandaloneConfigFieldsDirective,
    SubtaskListingDirective,
)
from .crossrefs import (
    config_ref_role,
    configfield_ref_role,
    pending_config_xref,
    pending_configfield_xref,
    pending_task_xref,
    process_pending_config_xref_nodes,
    process_pending_configfield_xref_nodes,
    process_pending_task_xref_nodes,
    task_ref_role,
)
from .pyapisummary import TaskApiDirective
from .topiclists import (
    CmdLineTaskListDirective,
    ConfigListDirective,
    ConfigurableListDirective,
    PipelineTaskListDirective,
    TaskListDirective,
    process_task_topic_list,
    task_topic_list,
)
from .topics import (
    ConfigTopicDirective,
    ConfigurableTopicDirective,
    TaskTopicDirective,
)


def setup(app):
    app.add_directive(
        ConfigFieldListingDirective.directive_name,
        ConfigFieldListingDirective,
    )
    app.add_directive(
        SubtaskListingDirective.directive_name, SubtaskListingDirective
    )
    app.add_directive(
        StandaloneConfigFieldsDirective.directive_name,
        StandaloneConfigFieldsDirective,
    )
    app.add_directive(TaskTopicDirective.directive_name, TaskTopicDirective)
    app.add_directive(
        ConfigurableTopicDirective.directive_name, ConfigurableTopicDirective
    )
    app.add_directive(
        ConfigTopicDirective.directive_name, ConfigTopicDirective
    )
    app.add_directive(TaskListDirective.directive_name, TaskListDirective)
    app.add_directive(
        CmdLineTaskListDirective.directive_name, CmdLineTaskListDirective
    )
    app.add_directive(
        PipelineTaskListDirective.directive_name, PipelineTaskListDirective
    )
    app.add_directive(
        ConfigurableListDirective.directive_name, ConfigurableListDirective
    )
    app.add_directive(ConfigListDirective.directive_name, ConfigListDirective)
    app.add_directive(TaskApiDirective.directive_name, TaskApiDirective)
    app.add_node(pending_task_xref)
    app.add_node(pending_config_xref)
    app.add_node(pending_configfield_xref)
    app.add_node(task_topic_list)
    app.connect("doctree-resolved", process_pending_task_xref_nodes)
    app.connect("doctree-resolved", process_pending_config_xref_nodes)
    app.connect("doctree-resolved", process_pending_configfield_xref_nodes)
    app.connect("doctree-resolved", process_task_topic_list)
    app.add_role("lsst-task", task_ref_role)
    app.add_role("lsst-config", config_ref_role)
    app.add_role("lsst-config-field", configfield_ref_role)

    return {"version": __version__}
