"""Stack documentation build system.
"""

from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from builtins import *  # NOQA
from future.standard_library import install_aliases
install_aliases()  # NOQA

import argparse
from collections import namedtuple
import logging
import os
import sys
import traceback

from docutils.utils import SystemMessage
from sphinx.errors import SphinxError
from sphinx.application import Sphinx
from sphinx.util import format_exception_cut_frames, save_traceback
from sphinx.util.console import red
from sphinx.util.docutils import docutils_namespace
from sphinx.util.pycompat import terminal_safe

import yaml

from .._version import get_versions
__version__ = get_versions()['version']
del get_versions


def run_build_cli():
    """Command line entrypoint for the ``build-stack-docs`` program.
    """
    args = parse_args()

    if args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s')

    logger = logging.getLogger(__name__)

    logger.info('build-stack-docs version {0}'.format(__version__))

    # Create the directory where module content is symlinked
    # NOTE: this path is hard-wired in for pipelines.lsst.io, but could be
    # refactored as a configuration.
    root_modules_dir = os.path.join(args.root_project_dir, 'modules')
    if os.path.isdir(root_modules_dir):
        logger.info('Deleting any existing modules/ symlinks')
        remove_existing_links(root_modules_dir)
    else:
        logger.info('Creating modules/ dir at {0}'.format(root_modules_dir))
        os.makedirs(root_modules_dir)

    # Create directory for package content
    root_packages_dir = os.path.join(args.root_project_dir, 'packages')
    if os.path.isdir(root_packages_dir):
        # Clear out existing module links
        logger.info('Deleting any existing packages/ symlinks')
        remove_existing_links(root_packages_dir)
    else:
        logger.info('Creating packages/ dir at {0}'.format(root_packages_dir))
        os.makedirs(root_packages_dir)

    # Ensure _static directory exists (but do not delete any existing
    # directory contents)
    root_static_dir = os.path.join(args.root_project_dir, '_static')
    if os.path.isdir(root_static_dir):
        # Clear out existing directory links
        logger.info('Deleting any existing _static/ symlinks')
        remove_existing_links(root_static_dir)
    else:
        logger.info('Creating _static/ at {0}'.format(root_static_dir))
        os.makedirs(root_static_dir)

    # Find package setup by EUPS
    packages = discover_setup_packages()

    # Link to documentation directories of packages from the root project
    for package_name, package_info in packages.items():
        try:
            package_docs = find_package_docs(package_info['dir'])
        except NoPackageDocs as e:
            logger.debug(
                'Skipping {0} doc linking. {1}'.format(package_name,
                                                       str(e)))
            continue

        link_directories(root_modules_dir, package_docs.module_dirs)
        link_directories(root_packages_dir, package_docs.package_dirs)
        link_directories(root_static_dir, package_docs.static_dirs)

    # Trigger the Sphinx build
    return_code = run_sphinx(args.root_project_dir)

    # Return code based on the Sphinx status.
    if return_code == 0:
        logger.info('build-stack-docs succeeded')
        sys.exit(0)
    else:
        logger.error('Sphinx errored: code {0:d}'.format(return_code))
        sys.exit(1)


def parse_args():
    """Create an argument parser for the ``build-stack-docs`` program.

    Returns
    -------
    args : `argparse.Namespace`
        Parsed argument object.
    """
    parser = argparse.ArgumentParser(
        description="Build a Sphinx documentation site for an EUPS stack, "
                    "such as pipelines.lsst.io.",
        epilog="Version {0}".format(__version__)
    )
    parser.add_argument(
        '-d', '--dir',
        dest='root_project_dir',
        help="Root Sphinx project directory")
    parser.add_argument(
        '-v', '--verbose',
        dest='verbose',
        action='store_true', default=False,
        help='Enable Verbose output (debug level logging)'
    )
    return parser.parse_args()


def discover_setup_packages():
    """Summarize packages currently set up by EUPS, listing their
    set up directories and EUPS version names.

    Returns
    -------
    packages : `dict`
       Dictionary with keys that are EUPS package names. Values are
       dictionaries with fields:

       - ``'dir'``: absolute directory path of the set up package.
       - ``'version'``: EUPS version string for package.

    Notes
    -----
    This function imports the ``eups`` Python package, which is assumed to
    be available in the build environmen. This function is designed to
    encapsulate all direct EUPS interactions need by the stack documentation
    build process.
    """
    logger = logging.getLogger(__name__)

    # Not a PyPI dependency; assumed to be available in the build environment.
    import eups

    eups_client = eups.Eups()
    products = eups_client.getSetupProducts()

    packages = {}
    for package in products:
        name = package.name
        info = {
            'dir': package.dir,
            'version': package.version
        }
        packages[name] = info
        logger.debug('Found setup package: {name} {version} {dir}'.format(
            name=name, **info))

    return packages


def find_package_docs(package_dir):
    """Find documentation directories in a package using ``manifest.yaml``.

    Parameters
    ----------
    package_dir : `str`
        Directory of an EUPS package.

    Returns
    -------
    doc_dirs : namedtuple
        Attributes of the namedtuple are:

        - ``package_dirs`` (`dict`). Keys are package names (for example,
          ``'afw'``). Values are absolute directory paths to the package's
          documentation directory inside the package's ``doc`` directory. If
          there is no package-level documentation the dictionary will be empty.

        - ``modules_dirs`` (`dict`). Keys are module names (for example,
          ``'lsst.afw.table'``). Values are absolute directory paths to the
          module's directory inside the package's ``doc`` directory. If a
          package has no modules the returned dictionary will be empty.

        - ``static_doc_dirs`` (`dict`). Keys are directory names relative to
          the ``_static`` directory. Values are absolute directory paths to
          the static documentation directory in the package.

    Raises
    ------
    NoPackageDocs
       Raised when the ``manifest.yaml`` file cannot be found in a package.

    Notes
    -----
    Stack packages have documentation in subdirectories of their `doc`
    directory. The ``manifest.yaml`` file declares what these directories are
    so that they can be symlinked into the root project.

    There are three types of documentation directories:

    1. Package doc directories contain documentation for the EUPS package
       aspect.
    2. Module doc directories contain documentation for a Python package
       aspect.
    3. Static doc directories are root directories inside the package's
       ``doc/_static/`` directory.

    These are declared in a package's ``doc/manifest.yaml`` file. For example:

    .. code-block:: yaml

       package: "afw"
       modules:
         - "lsst.afw.image"
         - "lsst.afw.geom"
       statics:
         - "_static/afw"

    This YAML declares *module* documentation directories:

    - ``afw/doc/lsst.afw.image/``
    - ``afw/doc/lsst.afw.geom/``

    It also declares a *package* documentation directory:

    - ``afw/doc/afw``

    And a static documentaton directory:

    - ``afw/doc/_static/afw``
    """
    logger = logging.getLogger(__name__)

    doc_dir = os.path.join(package_dir, 'doc')
    modules_yaml_path = os.path.join(doc_dir, 'manifest.yaml')

    if not os.path.exists(modules_yaml_path):
        raise NoPackageDocs(
            'Manifest YAML not found: {0}'.format(modules_yaml_path))

    with open(modules_yaml_path) as f:
        manifest_data = yaml.safe_load(f)

    module_dirs = {}
    package_dirs = {}
    static_dirs = {}

    if 'modules' in manifest_data:
        for module_name in manifest_data['modules']:
            module_dir = os.path.join(doc_dir, module_name)

            # validate that the module's documentation directory does exist
            if not os.path.isdir(module_dir):
                message = 'module doc dir not found: {0}'.format(module_dir)
                logger.warning(message)
                continue

            module_dirs[module_name] = module_dir
            logger.debug('Found module doc dir {0}'.format(module_dir))

    if 'package' in manifest_data:
        package_name = manifest_data['package']
        full_package_dir = os.path.join(doc_dir, package_name)

        # validate the directory exists
        if os.path.isdir(full_package_dir):
            package_dirs[package_name] = full_package_dir
            logger.debug('Found package doc dir {0}'.format(full_package_dir))
        else:
            logger.warning('package doc dir not found: {0}'.format(
                full_package_dir))

    if 'statics' in manifest_data:
        for static_dirname in manifest_data['statics']:
            full_static_dir = os.path.join(doc_dir, static_dirname)

            # validate the directory exists
            if not os.path.isdir(full_static_dir):
                message = '_static doc dir not found: {0}'.format(
                    full_static_dir)
                logger.warning(message)
                continue

            # Make a relative path to `_static` that's used as the
            # link source in the root docproject's _static/ directory
            relative_static_dir = os.path.relpath(
                full_static_dir,
                os.path.join(doc_dir, '_static'))

            static_dirs[relative_static_dir] = full_static_dir
            logger.debug('Found _static doc dir: {0}'.format(full_static_dir))

    Dirs = namedtuple('Dirs', ['module_dirs', 'package_dirs', 'static_dirs'])
    return Dirs(module_dirs=module_dirs,
                package_dirs=package_dirs,
                static_dirs=static_dirs)


class NoPackageDocs(Exception):
    """Exception raised when documentation is not found for an EUPS package.
    """


def link_directories(root_dir, package_doc_dirs):
    """Create symlinks to package/module documentation directories from the
    root documentation project.

    Parameters
    ----------
    root_dir : `str`
        Directory in the main documentation project where links will be
        created. For example, this could be a ``'modules'`` directory
        in the ``pipelines_lsst_io`` project directory.
    package_doc_dirs : `dict`
        Dictionary that maps symlinks to be made in ``root_dir`` with
        source directories in the packages.

    Notes
    -----
    If the link already exists in the ``root_dir`` it will be automatically
    replaced.
    """
    logger = logging.getLogger(__name__)

    for dirname, source_dirname in package_doc_dirs.items():
        link_name = os.path.join(root_dir, dirname)
        if os.path.islink(link_name):
            os.remove(link_name)
        os.symlink(source_dirname, link_name)

        message = 'Linking {0} -> {1}'.format(link_name, source_dirname)
        logger.info(message)


def remove_existing_links(root_dir):
    """Delete any symlinks present at the root of a directory.

    Parameters
    ----------
    root_dir : `str`
        Directory that might contain symlinks.

    Notes
    -----
    This function is used to remove any symlinks created by `link_directories`.
    Running ``remove_existing_links`` at the beginning of a build ensures that
    builds are isolated. For example, if a package is un-setup it won't
    re-appear in the documentation because its symlink still exists.
    """
    logger = logging.getLogger(__name__)

    for name in os.listdir(root_dir):
        full_name = os.path.join(root_dir, name)
        if os.path.islink(full_name):
            logger.debug('Deleting existing symlink {0}'.format(full_name))
            os.remove(full_name)


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

    # This replicates what Sphinx's internal command line hander does
    # https://github.com/sphinx-doc/sphinx/blob/master/sphinx/cmdline.py

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
        # NOTE: Sphinx 1.6+ also uses a
        # sphinx.util.docutils.patch_docutils() context
        with docutils_namespace():
            app = Sphinx(
                srcdir, confdir, outdir, doctreedir, builder,
                confoverrides, status, warning, freshenv,
                warningiserror, tags, verbosity, jobs)
            app.build(force_all, filenames)
            return app.statuscode
    except (Exception, KeyboardInterrupt) as exc:
        handle_sphinx_exception(app, exc, error)
        return 1


def handle_sphinx_exception(app, exception, stderr=sys.stderr):
    """Handle a Sphinx/docutils exception and print tracebacks.

    Parameters
    ----------
    app : `sphinx.application.Sphinx`
        Sphinx application object.
    exception : Exception
        Exception object.
    stderr : obj
        Typically `sys.stderr`.

    Notes
    -----
    This code is ported from Sphinx. Copyright 2007-2017 by the Sphinx team.
    See licenses/sphinx.txt for the full license.
    """
    print(file=stderr)
    traceback.print_exc(None, stderr)
    print(file=stderr)
    if isinstance(exception, KeyboardInterrupt):
        print('interrupted!', file=stderr)
    elif isinstance(exception, SystemMessage):
        print(red('reST markup error:'), file=stderr)
        print(terminal_safe(exception.args[0]), file=stderr)
    elif isinstance(exception, SphinxError):
        print(red('%s:' % exception.category), file=stderr)
        print(terminal_safe(str(exception)), file=stderr)
    elif isinstance(exception, UnicodeError):
        print(red('Encoding error:'), file=stderr)
        print(terminal_safe(str(exception)), file=stderr)
        tbpath = save_traceback(app)
        print(red('The full traceback has been saved in %s, if you want '
                  'to report the issue to the developers.' % tbpath),
              file=stderr)
    elif isinstance(exception, RuntimeError) \
            and 'recursion depth' in str(exception):
        print(red('Recursion error:'), file=stderr)
        print(terminal_safe(str(exception)), file=stderr)
        print(file=stderr)
        print('This can happen with very large or deeply nested source '
              'files.  You can carefully increase the default Python '
              'recursion limit of 1000 in conf.py with e.g.:', file=stderr)
        print('    import sys; sys.setrecursionlimit(1500)', file=stderr)
    else:
        print(red('Exception occurred:'), file=stderr)
        print(format_exception_cut_frames().rstrip(), file=stderr)
        tbpath = save_traceback(app)
        print(red('The full traceback has been saved in %s, if you '
                  'want to report the issue to the developers.' % tbpath),
              file=stderr)
