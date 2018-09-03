"""Utilities for working with LSST Task classes and their configurations.
"""

__all__ = ('get_task_config_class', 'get_subtask_fields', 'typestring')

from importlib import import_module
import inspect

from sphinx.errors import SphinxError


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


def typestring(obj):
    """Make a string for the object's type

    Parameters
    ----------
    obj : obj
        Python object.

    Returns
    -------
    `str`
        String representation of the object's type. This is the type's
        importable namespace.

    Examples
    --------
    >>> import docutils.nodes
    >>> para = docutils.nodes.paragraph()
    >>> typestring(para)
    'docutils.nodes.paragraph'
    """
    obj_type = type(obj)
    return '.'.join((obj_type.__module__, obj_type.__name__))
