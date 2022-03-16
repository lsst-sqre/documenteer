"""Utilities for detecting the root directory of Sphinx documentation.
"""

__all__ = ("discover_package_doc_dir", "discover_conf_py_directory")

import pathlib


def discover_package_doc_dir(initial_dir):
    """Discover the ``doc/`` dir of a package given an initial directory.

    Parameters
    ----------
    initial_dir : `str`
        The inititial directory to search from. In practice, this is often the
        directory that the user is running the package-docs CLI from. This
        directory needs to be somewhere inside the package's repository.

    Returns
    -------
    root_dir : `str`
        The root documentation directory (``doc/``), containing ``conf.py``.

    Raises
    ------
    FileNotFoundError
        Raised if a ``conf.py`` file is not found in the initial directory,
        or any parents, or in a ```doc/`` subdirectory.
    """
    # Create an absolute Path to work with
    initial_dir = pathlib.Path(initial_dir).resolve()

    # Check if this is the doc/ dir already with a conf.py
    if _has_conf_py(initial_dir):
        return str(initial_dir)

    # Search for a doc/ directory in cwd (this covers the case of running
    # the CLI from the root of a repository).
    test_dir = initial_dir / "doc"
    if test_dir.exists() and test_dir.is_dir():
        if _has_conf_py(test_dir):
            return str(test_dir)

    # Search upwards until a conf.py is found
    try:
        return str(_search_parents(initial_dir))
    except FileNotFoundError:
        raise


def discover_conf_py_directory(initial_dir):
    """Discover the directory containing the conf.py file.

    This function is useful for building stack docs since it will look in
    the current working directory and all parents.

    Parameters
    ----------
    initial_dir : `str`
        The inititial directory to search from. In practice, this is often the
        directory that the user is running the stack-docs CLI from.

    Returns
    -------
    root_dir : `str`
        The root documentation directory containing ``conf.py``.

    Raises
    ------
    FileNotFoundError
        Raised if a ``conf.py`` file is not found in the initial directory,
        or any parents.
    """
    # Create an absolute Path to work with
    initial_dir = pathlib.Path(initial_dir).resolve()

    # Search upwards until a conf.py is found
    try:
        return str(_search_parents(initial_dir))
    except FileNotFoundError:
        raise


def _has_conf_py(root_dir):
    if (root_dir / "conf.py").exists():
        return True
    else:
        return False


def _search_parents(initial_dir):
    """Search the initial and parent directories for a ``conf.py`` Sphinx
    configuration file that represents the root of a Sphinx project.

    Returns
    -------
    root_dir : `pathlib.Path`
        Directory path containing a ``conf.py`` file.

    Raises
    ------
    FileNotFoundError
        Raised if a ``conf.py`` file is not found in the initial directory
        or any parents.
    """
    root_paths = (".", "/")
    parent = pathlib.Path(initial_dir)
    while True:
        if _has_conf_py(parent):
            return parent
        if str(parent) in root_paths:
            break
        parent = parent.parent
    msg = (
        "Cannot detect a conf.py Sphinx configuration file from {!s}. "
        "Are you inside a Sphinx documenation repository?"
    ).format(initial_dir)
    raise FileNotFoundError(msg)
