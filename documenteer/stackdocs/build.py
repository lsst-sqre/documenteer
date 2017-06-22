"""Stack documentation build system.
"""

from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from builtins import *  # NOQA
from future.standard_library import install_aliases
install_aliases()  # NOQA

import argparse
from collections import namedtuple
import os
import shutil

import yaml


def run_build_cli():
    """Command line entrypoint for the ``build-stack-docs`` program.
    """
    args = parse_args()

    # Create the directory where module content is symlinked
    # NOTE: this path is hard-wired in for pipelines.lsst.io, but could be
    # refactored as a configuration.
    root_modules_dir = os.path.join(args.root_project_dir, 'modules')
    if os.path.isdir(root_modules_dir):
        # Clear out existing module links
        shutil.rmtree(root_modules_dir)
    os.makedirs(root_modules_dir)

    # Create directory for package content
    root_packages_dir = os.path.join(args.root_project_dir, 'packages')
    if os.path.isdir(root_packages_dir):
        # Clear out existing module links
        shutil.rmtree(root_packages_dir)
    os.makedirs(root_packages_dir)

    # Ensure _static directory exists (but do not delete any existing
    # directory contents
    root_static_dir = os.path.join(args.root_project_dir, '_static')
    if not os.path.isdir(root_static_dir):
        os.makedirs(root_static_dir)

    # Find package setup by EUPS
    packages = discover_setup_packages()

    # Link module documentation directories of packages into the
    # root project's module documentation directory
    for package_name, package_info in packages.items():
        package_docs = find_package_docs(package_info['dir'])
        link_directories(root_modules_dir, package_docs.module_dirs)
        link_directories(root_packages_dir, package_docs.package_dirs)
        link_directories(root_static_dir, package_docs.static_dirs)

    # TODO: trigger the Sphinx build


def parse_args():
    """Create an argument parser for the ``build-stack-docs`` program.

    Returns
    -------
    args : `argparse.Namespace`
        Parsed argument object.
    """
    # Get version from versioneer
    from .._version import get_versions

    parser = argparse.ArgumentParser(
        description="Build a Sphinx documentation site for an EUPS stack, "
                    "such as pipelines.lsst.io.",
        epilog="Version {0}".format(get_versions()['version'])
    )
    parser.add_argument(
        '-d', '--dir',
        dest='root_project_dir',
        help="Root Sphinx project directory")
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
    IOError
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
    doc_dir = os.path.join(package_dir, 'doc')
    modules_yaml_path = os.path.join(doc_dir, 'manifest.yaml')

    if not os.path.exists(modules_yaml_path):
        raise IOError('Manifest YAML not found: {0}'.format(modules_yaml_path))

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
                continue

            module_dirs[module_name] = module_dir

    if 'package' in manifest_data:
        package_name = manifest_data['package']
        full_package_dir = os.path.join(doc_dir, package_name)

        # validate the directory exists
        if os.path.isdir(full_package_dir):
            package_dirs[package_name] = full_package_dir

    if 'statics' in manifest_data:
        for static_dirname in manifest_data['statics']:
            full_static_dir = os.path.join(doc_dir, static_dirname)

            # validate the directory exists
            if not os.path.isdir(full_static_dir):
                continue

            # Make a relative path to `_static` that's used as the
            # link source in the root docproject's _static/ directory
            relative_static_dir = os.path.relpath(
                full_static_dir,
                os.path.join(doc_dir, '_static'))

            static_dirs[relative_static_dir] = full_static_dir

    Dirs = namedtuple('Dirs', ['module_dirs', 'package_dirs', 'static_dirs'])
    return Dirs(module_dirs=module_dirs,
                package_dirs=package_dirs,
                static_dirs=static_dirs)


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
    for dirname, source_dirname in package_doc_dirs.items():
        link_name = os.path.join(root_dir, dirname)
        if os.path.islink(link_name):
            os.remove(link_name)
        os.symlink(source_dirname, link_name)
