"""Sphinx/docutils extensions for LSST DM documentation.

Enable these extension by adding ``documenteer.sphinxext`` to your
extensions list in :file:`conf.py`::

    extensions = [
       # ...
       'documenteer.sphinxext'
    ]

Some extensions require project-specific dependencies and are not
automatically enabled. They should be specified individually. They are:

- ``documenteer.sphinxext.bibtex``
"""

__all__ = ('setup',)

from pkg_resources import get_distribution, DistributionNotFound

from . import (jira, lsstdocushare, mockcoderefs, packagetoctree,
               remotecodeblock)


def setup(app):
    """Wrapper for the `setup` functions of each individual extension module.
    """
    jira.setup(app)
    lsstdocushare.setup(app)
    mockcoderefs.setup(app)
    packagetoctree.setup(app)
    remotecodeblock.setup(app)

    try:
        __version__ = get_distribution('documenteer').version
    except DistributionNotFound:
        # package is not installed
        __version__ = 'unknown'
    return {'version': __version__,
            'parallel_read_safe': True,
            'parallel_write_safe': True}
