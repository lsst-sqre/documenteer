"""Sphinx extensions for summarizing the Python API for tasks.
"""

__all__ = ('TaskApiDirective',)


from docutils.parsers.rst import Directive
from sphinx.errors import SphinxError
from sphinx.util.logging import getLogger
from sphinx.util.inspect import getdoc
from sphinx.util.docstrings import prepare_docstring

from .taskutils import get_type


class TaskApiDirective(Directive):
    """``lsst-task-api-summary`` directive that renders a summary of a LSST
    Science Pipelines Task's Python API and links to the regular Python API
    documentation from ``automodapi``.
    """

    directive_name = 'lsst-task-api-summary'
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
        logger = getLogger(__name__)

        try:
            task_class_name = self.arguments[0]
        except IndexError:
            raise SphinxError(
                '{} directive requires a Task class '
                'name as an argument'.format(self.directive_name))

        logger.debug(
            '%s running with %r', self.directive_name, task_class_name)

        task_class = get_type(task_class_name)


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
    """
    docstring = getdoc(obj, allow_inherited=True)
    # ignore is simply the number of initial lines to ignore when determining
    # the docstring's baseline indent level. We really want "1" here.
    return prepare_docstring(docstring, ignore=1)


def extract_docstring_summary(docstring):
    """Get the first summary sentence from a docstring.

    Parameters
    ----------
    docstring : `list` of `str`
        Output from `get_docstring`.

    Returns
    -------
    summary : `str`
        The plain-text summary sentence from teh docstring.
    """
    summary_lines = []
    for line in docstring:
        if line == '':
            break
        else:
            summary_lines.append(line)
    return ' '.join(summary_lines)
