"""Sphinx extensions for documenting LSST Science Pipelines Tasks.
"""

__all__ = ('setup',)

from pkg_resources import get_distribution, DistributionNotFound

from .subtasks import SubtasksDirective
from .taskconfigs import TaskConfigsDirective


def setup(app):
    app.add_directive('lsst-subtasks', SubtasksDirective)
    app.add_directive('lsst-task-configs', TaskConfigsDirective)

    try:
        __version__ = get_distribution('documenteer').version
    except DistributionNotFound:
        # package is not installed
        __version__ = 'unknown'
    return {'version': __version__}
