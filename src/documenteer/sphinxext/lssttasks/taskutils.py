"""Utilities for working with LSST Task classes and their configurations.
"""

__all__ = (
    "get_task_config_class",
    "get_task_config_fields",
    "get_subtask_fields",
    "typestring",
    "get_type",
    "get_docstring",
    "extract_docstring_summary",
)

import inspect
from importlib import import_module

from sphinx.errors import SphinxError
from sphinx.util.docstrings import prepare_docstring
from sphinx.util.inspect import getdoc
from sphinx.util.logging import getLogger


def get_task_config_class(task_name):
    """Get the Config class for a task given its fully-qualified name.

    Parameters
    ----------
    task_name : `str`
        Name of the task, such as ``lsst.pipe.tasks.processCcd.ProcessCcdTask`.

    Returns
    -------
    config_class : ``lsst.pipe.base.Config``-type
        The configuration class (not an instance) corresponding to the task.
    """
    task_class = get_type(task_name)

    return task_class.ConfigClass


def get_type(type_name):
    """Get a type given its importable name.

    Parameters
    ----------
    task_name : `str`
        Name of the Python type, such as ``mypackage.MyClass``.

    Returns
    -------
    object
        The object.
    """
    parts = type_name.split(".")
    if len(parts) < 2:
        raise SphinxError(
            "Type must be fully-qualified, "
            "of the form ``module.MyClass``. Got: {}".format(type_name)
        )
    module_name = ".".join(parts[0:-1])
    name = parts[-1]
    return getattr(import_module(module_name), name)


def get_task_config_fields(config_class):
    """Get all configuration Fields from a Config class.

    Parameters
    ----------
    config_class : ``lsst.pipe.base.Config``-type
        The configuration class (not an instance) corresponding to a Task.

    Returns
    -------
    config_fields : `dict`
        Mapping where keys are the config attribute names and values are
        subclasses of ``lsst.pex.config.Field``. The mapping is alphabetically
        ordered by attribute name.
    """
    from lsst.pex.config import Field

    def is_config_field(obj):
        return isinstance(obj, Field)

    return _get_alphabetical_members(config_class, is_config_field)


def get_subtask_fields(config_class):
    """Get all configurable subtask fields from a Config class.

    Parameters
    ----------
    config_class : ``lsst.pipe.base.Config``-type
        The configuration class (not an instance) corresponding to a Task.

    Returns
    -------
    subtask_fields : `dict`
        Mapping where keys are the config attribute names and values are
        subclasses of ``lsst.pex.config.ConfigurableField`` or
        ``RegistryField``). The mapping is alphabetically ordered by
        attribute name.
    """
    from lsst.pex.config import ConfigurableField, RegistryField

    def is_subtask_field(obj):
        return isinstance(obj, (ConfigurableField, RegistryField))

    return _get_alphabetical_members(config_class, is_subtask_field)


def _get_alphabetical_members(obj, predicate):
    """Get members of an object, sorted alphabetically.

    Parameters
    ----------
    obj
        An object.
    predicate : callable
        Callable that takes an attribute and returns a bool of whether the
        attribute should be returned or not.

    Returns
    -------
    members : `dict`
        Dictionary of

        - Keys: attribute name
        - Values: attribute

        The dictionary is ordered according to the attribute name.

    Notes
    -----
    This uses the insertion-order-preserved nature of `dict` in Python 3.6+.

    See also
    --------
    `inspect.getmembers`
    """
    fields = dict(inspect.getmembers(obj, predicate))
    keys = list(fields.keys())
    keys.sort()
    return {k: fields[k] for k in keys}


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
    return ".".join((obj_type.__module__, obj_type.__name__))


def get_docstring(obj):
    """Extract the docstring from an object as individual lines.

    Parameters
    ----------
    obj : object
        The Python object (class, function or method) to extract docstrings
        from.

    Returns
    -------
    lines : `list` of `str`
        Individual docstring lines with common indentation removed, and
        newline characters stripped.

    Notes
    -----
    If the object does not have a docstring, a docstring with the content
    ``"Undocumented."`` is created.
    """
    docstring = getdoc(obj, allow_inherited=True)
    if docstring is None:
        logger = getLogger(__name__)
        logger.warning("Object %s doesn't have a docstring.", obj)
        docstring = "Undocumented"
    # ignore is simply the number of initial lines to ignore when determining
    # the docstring's baseline indent level. We really want "1" here.
    return prepare_docstring(docstring)


def extract_docstring_summary(docstring):
    """Get the first summary sentence from a docstring.

    Parameters
    ----------
    docstring : `list` of `str`
        Output from `get_docstring`.

    Returns
    -------
    summary : `str`
        The plain-text summary sentence from the docstring.
    """
    summary_lines = []
    for line in docstring:
        if line == "":
            break
        else:
            summary_lines.append(line)
    return " ".join(summary_lines)
