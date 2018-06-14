"""Run Sphinx directly through its Python API.
"""

__all__ = ('run_sphinx',)

import os
import logging
import sys

from sphinx.application import Sphinx
try:
    from sphinx.cmd.build import handle_exception
except ImportError:
    # Sphinx <1.8
    from sphinx.cmdline import handle_exception
from sphinx.util.docutils import docutils_namespace, patch_docutils


def run_sphinx(root_dir):
    """Run the Sphinx build process.

    Parameters
    ----------
    root_dir : `str`
        Root directory of the Sphinx project and content source. This directory
        conatains both the root ``index.rst`` file and the ``conf.py``
        configuration file.

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
    logger = logging.getLogger(__name__)

    # This replicates what Sphinx's internal command line hander does in
    # https://github.com/sphinx-doc/sphinx/blob/master/sphinx/cmd/build.py
    # build_main()

    # configuration
    root_dir = os.path.abspath(root_dir)
    srcdir = root_dir  # root directory of Sphinx content
    confdir = root_dir  # directory where conf.py is located
    outdir = os.path.join(root_dir, '_build', 'html')
    doctreedir = os.path.join(root_dir, '_build', 'doctree')
    builder = 'html'
    confoverrides = {}
    status = sys.stdout  # set to None for 'quiet' mode
    warning = sys.stderr
    error = sys.stderr
    freshenv = False  # attempt to re-use existing build artificats
    warningiserror = False
    tags = []
    verbosity = 0
    jobs = 1  # number of processes
    force_all = True
    filenames = []

    logger.debug('Sphinx config: srcdir={0}'.format(srcdir))
    logger.debug('Sphinx config: confdir={0}'.format(confdir))
    logger.debug('Sphinx config: outdir={0}'.format(outdir))
    logger.debug('Sphinx config: doctreedir={0}'.format(doctreedir))
    logger.debug('Sphinx config: builder={0}'.format(builder))
    logger.debug('Sphinx config: freshenv={0:b}'.format(freshenv))
    logger.debug('Sphinx config: warningiserror={0:b}'.format(warningiserror))
    logger.debug('Sphinx config: verbosity={0:d}'.format(verbosity))
    logger.debug('Sphinx config: jobs={0:d}'.format(jobs))
    logger.debug('Sphinx config: force_all={0:b}'.format(force_all))

    app = None
    try:
        with patch_docutils(), docutils_namespace():
            app = Sphinx(
                srcdir, confdir, outdir, doctreedir, builder,
                confoverrides, status, warning, freshenv,
                warningiserror, tags, verbosity, jobs)
            app.build(force_all, filenames)
            return app.statuscode
    except (Exception, KeyboardInterrupt) as exc:
        args = MockSphinxNamespace(verbosity=verbosity, traceback=True)
        handle_exception(app, args, exc, error)
        return 1


class MockSphinxNamespace:
    """Mock Namespace object to mock the Sphinx command line arguments.

    This class is needed for sphinx.cmd.build.handle_exception.
    """

    def __init__(self, verbosity=0, traceback=True):
        self.verbosity = verbosity
        self.traceback = traceback
        self.pdb = False
