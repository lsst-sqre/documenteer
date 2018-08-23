"""Sphinx directive ``lsst-subtasks`` that documents the subtasks in a Task's
Config class.
"""

__all__ = ('setup', 'SubtasksDirective')

from importlib import import_module
import inspect

from docutils.parsers.rst import Directive
try:
    # Sphinx 1.6+
    from sphinx.util.logging import getLogger
except ImportError:
    getLogger = None
from sphinx.errors import SphinxError
from pkg_resources import get_distribution, DistributionNotFound


class SubtasksDirective(Directive):
    """``lsst-subtasks`` directive that renders documentation for the subtasks
    associated with an ``lsst.pipe.base.Task``.
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
        if getLogger is not None:
            # Sphinx 1.6+
            logger = getLogger(__name__)
        else:
            # Previously Sphinx's app was also the logger
            logger = self.state.document.settings.env.app

        try:
            task_class_name = self.arguments[0]
        except IndexError:
            raise SphinxError('lsst-subtasks directive requires a Task class '
                              'name as an argument')
        logger.debug('lsst-subtasks using Task class %s', task_class_name)


def get_task_config_class(task_name):
    """Get the Config class for a task given its fully-qualified name.

    Parameters
    ----------
    task_name : `str`
        Name of the task, such as ``lsst.pipe.tasks.processCcd.ProcessCcdTask`.

    Returns
    -------
    config_class : ``lsst.pipe.base.Config``\ -type
        The configuration class (not an instance) corresponding to the task.
    """
    parts = task_name.split('.')
    if len(parts) < 2:
        raise SphinxError(
            'The Task class must be fully-qualified, '
            'of the form ``module.TaskName``. Got: {}'.format(task_name)
        )
    module_name = ".".join(parts[0:-1])
    task_class_name = parts[-1]
    task_class = getattr(import_module(module_name), task_class_name)

    return task_class.ConfigClass


def get_subtask_fields(config_class):
    """Get all configurable subtask fields from a Config class.

    Parameters
    ----------
    config_class : ``lsst.pipe.base.Config``\ -type
        The configuration class (not an instance) corresponding to a Task.

    Returns
    -------
    subtask_fields : `dict`
        Mapping where keys are the config attribute names and values are
        subclasses of ``lsst.pex.config.Field`` (or specifically
        ``ConfigurableField``).
    """
    from lsst.pex.config import ConfigurableField

    def is_subtask_field(obj):
        return isinstance(obj, ConfigurableField)

    return dict(inspect.getmembers(config_class, is_subtask_field))


def setup(app):
    app.add_directive('lsst-subtasks', SubtasksDirective)

    try:
        __version__ = get_distribution('documenteer').version
    except DistributionNotFound:
        # package is not installed
        __version__ = 'unknown'
    return {'version': __version__}
