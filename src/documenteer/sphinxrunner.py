"""Run Sphinx directly through its Python API."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Union

from sphinx.cmd.build import build_main

__all__ = ["run_sphinx"]


def run_sphinx(
    root_dir: Union[str, Path],
    job_count: int = 1,
    warnings_as_errors: bool = False,
) -> int:
    """Run the Sphinx build process.

    Parameters
    ----------
    root_dir : `str`
        Root directory of the Sphinx project and content source. This directory
        contains both the root ``index.rst`` file and the ``conf.py``
        configuration file.
    job_count : `int`
        Number of cores to run the Sphinx build with (``-j`` flag)

    Returns
    -------
    status : `int`
        Sphinx status code. ``0`` is expected. Greater than ``0`` indicates
        an error.

    Notes
    -----
    This function implements similar internals to Sphinx's own ``sphinx-build``
    command. Most configurations are hard-coded to defaults appropriate for
    building stack documentation, but flexibility can be added later as
    needs are identified.
    """
    src_dir = str(os.path.abspath(root_dir))

    argv = [
        f"-j {job_count}",
        "-b",
        "html",
        "-d",
        os.path.join("_build", ".doctrees"),
    ]
    if warnings_as_errors:
        argv.append("-W")
    argv.extend([src_dir, os.path.join("_build", "html")])

    start_dir = os.path.abspath(".")
    try:
        os.chdir(src_dir)
        status = build_main(argv=argv)
    finally:
        os.chdir(start_dir)
    return status
