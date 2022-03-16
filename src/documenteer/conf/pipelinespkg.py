"""Sphinx configuration for a single-package documentation builds for packages
in pipelines.lsst.io.

For usage, see:

    https://documenteer.lsst.io/pipelines/configuration.html#pipelinespkg-conf
"""

from .pipelines import *  # noqa: F401 F403

# ============================================================================
# todo extension configuration
# ============================================================================
# Show todo directives in the development documentation for single packages.
todo_include_todos = True
