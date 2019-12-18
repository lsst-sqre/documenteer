"""Stack documentation build system.
"""

__all__ = ('run_build_cli', 'build_stack_docs')

import argparse
import logging
import os
import sys
import re

from pkg_resources import get_distribution, DistributionNotFound

from .pkgdiscovery import find_package_docs, NoPackageDocs
from ..sphinxrunner import run_sphinx

try:
    __version__ = get_distribution('documenteer').version
except DistributionNotFound:
    # package is not installed
    __version__ = 'unknown'


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

    return_code = build_stack_docs(args.root_project_dir)
    if return_code == 0:
        logger.info('build-stack-docs succeeded')
        sys.exit(0)
    else:
        logger.error('Sphinx errored: code {0:d}'.format(return_code))
        sys.exit(1)


def build_stack_docs(root_project_dir, skippedNames=None):
    """Build stack Sphinx documentation (main entrypoint).

    Parameters
    ----------
    root_project_dir : `str`
        Path to the root directory of the main documentation project. This
        is the directory containing the ``conf.py`` file.
    skippedNames : `list`, optional
        Optional list of packages to skip while creating symlinks.
    """
    logger = logging.getLogger(__name__)

    # Create the directory where module content is symlinked
    # NOTE: this path is hard-wired in for pipelines.lsst.io, but could be
    # refactored as a configuration.
    root_modules_dir = os.path.join(root_project_dir, 'modules')
    if os.path.isdir(root_modules_dir):
        logger.info('Deleting any existing modules/ symlinks')
        remove_existing_links(root_modules_dir)
    else:
        logger.info('Creating modules/ dir at {0}'.format(root_modules_dir))
        os.makedirs(root_modules_dir)

    # Create directory for package content
    root_packages_dir = os.path.join(root_project_dir, 'packages')
    if os.path.isdir(root_packages_dir):
        # Clear out existing module links
        logger.info('Deleting any existing packages/ symlinks')
        remove_existing_links(root_packages_dir)
    else:
        logger.info('Creating packages/ dir at {0}'.format(root_packages_dir))
        os.makedirs(root_packages_dir)

    # Ensure _static directory exists (but do not delete any existing
    # directory contents)
    root_static_dir = os.path.join(root_project_dir, '_static')
    if os.path.isdir(root_static_dir):
        # Clear out existing directory links
        logger.info('Deleting any existing _static/ symlinks')
        remove_existing_links(root_static_dir)
    else:
        logger.info('Creating _static/ at {0}'.format(root_static_dir))
        os.makedirs(root_static_dir)

    # Find package setup by EUPS
    packages = discover_setup_packages()

    # Get packages explicitly required in the table file to filter out
    # implicit dependencies later.
    table_path = find_table_file(root_project_dir)
    with open(table_path) as fp:
        table_data = fp.read()
    listed_packages = list_packages_in_eups_table(table_data)

    # Link to documentation directories of packages from the root project
    for package_name, package_info in packages.items():
        if package_name not in listed_packages:
            logger.debug(
                'Filtering %s from build since it is not explictly '
                'required by the %s table file.',
                package_name, table_path)
            continue
        try:
            package_docs = find_package_docs(
                package_info['dir'],
                skipped_names=skippedNames)
        except NoPackageDocs as e:
            logger.debug(
                'Skipping %s doc linking. %s', package_name, e)
            continue

        link_directories(root_modules_dir, package_docs.module_dirs)
        link_directories(root_packages_dir, package_docs.package_dirs)
        link_directories(root_static_dir, package_docs.static_doc_dirs)

    # Trigger the Sphinx build
    return_code = run_sphinx(root_project_dir)
    return return_code


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


def find_table_file(root_project_dir):
    """Find the EUPS table file for a project.

    Parameters
    ----------
    root_project_dir : `str`
        Path to the root directory of the main documentation project. This
        is the directory containing the ``conf.py`` file and a ``ups``
        directory.

    Returns
    -------
    table_path : `str`
        Path to the EUPS table file.
    """
    ups_dir_path = os.path.join(root_project_dir, 'ups')
    table_path = None
    for name in os.listdir(ups_dir_path):
        if name.endswith('.table'):
            table_path = os.path.join(ups_dir_path, name)
            break
    if not os.path.exists(table_path):
        raise RuntimeError(
            'Could not find the EUPS table file at {}'.format(table_path))
    return table_path


def list_packages_in_eups_table(table_text):
    """List the names of packages that are required by an EUPS table file.

    Parameters
    ----------
    table_text : `str`
        The text content of an EUPS table file.

    Returns
    -------
    names : `list` [`str`]
        List of package names that are required byy the EUPS table file.
    """
    logger = logging.getLogger(__name__)
    # This pattern matches required product names in EUPS table files.
    pattern = re.compile(r'setupRequired\((?P<name>\w+)\)')
    listed_packages = [m.group('name') for m in pattern.finditer(table_text)]
    logger.debug('Packages listed in the table file: %r', listed_packages)
    return listed_packages


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
