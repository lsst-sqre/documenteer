"""Sphinx extensions for summarizing the Python API for tasks.
"""

from sphinx.util.inspect import getdoc
from sphinx.util.docstrings import prepare_docstring


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
