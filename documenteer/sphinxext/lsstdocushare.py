"""LSST Docushare reference roles."""

from __future__ import (division, absolute_import, print_function,
                        unicode_literals)
from builtins import *  # NOQA
from future.standard_library import install_aliases
install_aliases()  # NOQA

import logging

from docutils import nodes


log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def lsst_doc_shortlink_role(name, rawtext, text, lineno, inliner,
                            options=None, content=None):
    """Link to LSST documents given their handle using LSST's ls.st link
    shortener.

    Compatible with 'LDM,' 'LSE,' and 'LPM' documents.

    Example::

        :ldm:`151`
    """
    options = options or {}
    content = content or []
    node = nodes.reference(
        text='{0}-{1}'.format(name.upper(), text),
        refuri='http://ls.st/{0}-{1}'.format(name, text),
        **options)
    return [node], []


def setup(app):
    app.add_role('ldm', lsst_doc_shortlink_role)
    app.add_role('lse', lsst_doc_shortlink_role)
    app.add_role('lpm', lsst_doc_shortlink_role)
