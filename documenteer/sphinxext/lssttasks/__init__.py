"""Sphinx extensions for documenting LSST Science Pipelines Tasks.
"""

__all__ = ('setup',)

from pkg_resources import get_distribution, DistributionNotFound

from .subtasks import SubtasksDirective
from .taskconfigs import TaskConfigsDirective
from .standaloneconfigs import StandaloneConfigsDirective
from .crossrefs import (
    TaskTopicTargetDirective, ConfigurableTopicTargetDirective,
    ConfigTopicTargetDirective, pending_task_xref, pending_config_xref,
    task_ref_role, config_ref_role, process_pending_task_xref_nodes,
    process_pending_config_xref_nodes)


def setup(app):
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
    app.add_directive(
        TaskTopicTargetDirective.directive_name, TaskTopicTargetDirective)
    app.add_directive(
        ConfigurableTopicTargetDirective.directive_name,
        ConfigurableTopicTargetDirective)
    app.add_directive(
        ConfigTopicTargetDirective.directive_name,
        ConfigTopicTargetDirective)
    app.add_node(pending_task_xref)
    app.add_node(pending_config_xref)
    app.connect('doctree-resolved', process_pending_task_xref_nodes)
    app.connect('doctree-resolved', process_pending_config_xref_nodes)
    app.add_role('lsst-task', task_ref_role)
    app.add_role('lsst-config', config_ref_role)

    try:
        __version__ = get_distribution('documenteer').version
    except DistributionNotFound:
        # package is not installed
        __version__ = 'unknown'
    return {'version': __version__}
