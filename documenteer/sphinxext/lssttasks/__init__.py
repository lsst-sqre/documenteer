"""Sphinx extensions for documenting LSST Science Pipelines Tasks.
"""

__all__ = ('setup',)

from pkg_resources import get_distribution, DistributionNotFound

from ..utils import SphinxExtension
extension = SphinxExtension()  # noqa: E402

from .subtasks import SubtasksDirective
from .taskconfigs import TaskConfigsDirective
from .standaloneconfigs import StandaloneConfigsDirective
from .topics import *  # noqa: F401, F403
from .crossrefs import (
    pending_task_xref, pending_config_xref,
    pending_configfield_xref, task_ref_role, config_ref_role,
    configfield_ref_role, process_pending_task_xref_nodes,
    process_pending_config_xref_nodes, process_pending_configfield_xref_nodes)
from .pyapisummary import TaskApiDirective
from .topiclists import (
    TaskListDirective, CmdLineTaskListDirective, PipelineTaskListDirective,
    ConfigurableListDirective, ConfigListDirective,
    task_topic_list, process_task_topic_list)


def setup(app):
    extension.setup(app)
    app.add_directive(
        SubtasksDirective.directive_name,
        SubtasksDirective)
    app.add_directive(
        TaskConfigsDirective.directive_name,
        TaskConfigsDirective,
    )
    app.add_directive(
        StandaloneConfigsDirective.directive_name,
        StandaloneConfigsDirective
    )
    # app.add_directive(
    #     TaskTopicDirective.directive_name, TaskTopicDirective)
    # app.add_directive(
    #     ConfigurableTopicDirective.directive_name,
    #     ConfigurableTopicDirective)
    # app.add_directive(
    #     ConfigTopicDirective.directive_name,
    #     ConfigTopicDirective)
    app.add_directive(
        TaskListDirective.directive_name,
        TaskListDirective)
    app.add_directive(
        CmdLineTaskListDirective.directive_name,
        CmdLineTaskListDirective)
    app.add_directive(
        PipelineTaskListDirective.directive_name,
        PipelineTaskListDirective)
    app.add_directive(
        ConfigurableListDirective.directive_name,
        ConfigurableListDirective)
    app.add_directive(
        ConfigListDirective.directive_name,
        ConfigListDirective)
    app.add_directive(
        TaskApiDirective.directive_name,
        TaskApiDirective)
    app.add_node(pending_task_xref)
    app.add_node(pending_config_xref)
    app.add_node(pending_configfield_xref)
    app.add_node(task_topic_list)
    app.connect('doctree-resolved', process_pending_task_xref_nodes)
    app.connect('doctree-resolved', process_pending_config_xref_nodes)
    app.connect('doctree-resolved', process_pending_configfield_xref_nodes)
    app.connect('doctree-resolved', process_task_topic_list)
    app.add_role('lsst-task', task_ref_role)
    app.add_role('lsst-config', config_ref_role)
    app.add_role('lsst-config-field', configfield_ref_role)

    try:
        __version__ = get_distribution('documenteer').version
    except DistributionNotFound:
        # package is not installed
        __version__ = 'unknown'
    return {'version': __version__}
