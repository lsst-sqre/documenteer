"""Utilities used internally be Documenteer.
"""

__all__ = "working_directory"

import contextlib
import os
from pathlib import Path
from typing import Generator, Union


@contextlib.contextmanager
def working_directory(path: Union[Path, str]) -> Generator:
    """A context manager that temporarily changes the current working
    directory.

    Parameters
    ----------
    path
        Path of the new current working directory. Either a `pathlib` path or
        a string representation of a directory.

    Examples
    --------
    >>> from pathlib import Path
    >>> import os
    >>> p = Path('mydir')
    >>> os.makedirs(p)
    >>> filepath = p / 'myfile.txt'
    >>> filepath.write_text('hello')
    >>> with working_directory(p):
    ...     print(Path('myfile.txt').read_text())
    hello
    """
    original_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(original_cwd)
