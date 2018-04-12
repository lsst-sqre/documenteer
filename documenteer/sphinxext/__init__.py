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

from . import jira, lsstdocushare, mockcoderefs, packagetoctree


def setup(app):
    """Wrapper for the `setup` functions of each individual extension module.
    """
    jira.setup(app)
    lsstdocushare.setup(app)
    mockcoderefs.setup(app)
    packagetoctree.setup(app)
