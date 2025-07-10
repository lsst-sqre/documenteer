"""Utilities used internally be Documenteer."""

__all__ = ["working_directory"]

import contextlib
import os
from collections.abc import Generator
from pathlib import Path


@contextlib.contextmanager
def working_directory(path: Path | str) -> Generator:
    """Temporarily change the current working directory in context.

    Parameters
    ----------
    path
        Path of the new current working directory. Either a `pathlib` path or
        a string representation of a directory.

    Examples
    --------
    >>> from pathlib import Path
    >>> import os
    >>> p = Path("mydir")
    >>> os.makedirs(p)
    >>> filepath = p / "myfile.txt"
    >>> filepath.write_text("hello")
    >>> with working_directory(p):
    ...     print(Path("myfile.txt").read_text())
    hello
    """
    original_cwd = Path.cwd()
    os.chdir(Path(path))
    try:
        yield
    finally:
        os.chdir(original_cwd)
