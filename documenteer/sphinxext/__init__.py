"""Sphinx/docutils extensions for LSST DM documentation.

Enable these extension by adding `documenteer.sphinxext` to your
extensions list in :file:`conf.py`::

    extensions = [
       # ...
       'documenteer.sphinxext'
    ]
"""

from . import jira, lsstdocushare, mockcoderefs


def setup(app):
    """Wrapper for the `setup` functions of each individual extension module.
    """
    jira.setup(app)
    lsstdocushare.setup(app)
    mockcoderefs.setup(app)
