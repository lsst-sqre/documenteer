"""Stack documentation build system.
"""

__all__ = ('build_stack_docs',)

import logging
import os
from typing import Dict

from .pkgdiscovery import (
    discover_setup_packages, find_table_file, list_packages_in_eups_table,
    find_package_docs, NoPackageDocs, Package)
from .doxygen import (
    DoxygenConfiguration, preprocess_package_doxygen_conf, run_doxygen)
from ..sphinxrunner import run_sphinx


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

    # Get packages explicitly required in the table file to filter out
    # implicit dependencies later.
    table_path = find_table_file(root_project_dir)
    listed_packages = list_packages_in_eups_table(table_path.read_text())
    # Find package setup by EUPS
    set_up_packages = discover_setup_packages(scope=listed_packages)

    # Determine what packages have documentation content, and get Package
    # metadata objects about those
    packages: Dict[str, Package] = {}
    for package_name, package_info in set_up_packages.items():
        try:
            package_docs = find_package_docs(
                package_info['dir'],
                skipped_names=skippedNames)
            packages[package_name] = package_docs
        except NoPackageDocs as e:
            logger.debug(
                'Skipping %s doc linking. %s', package_name, e)
            continue

    # Link to documentation directories of packages from the root project
    for package_name, package in packages.items():
        link_directories(root_modules_dir, package.module_dirs)
        link_directories(root_packages_dir, package.package_dirs)
        link_directories(root_static_dir, package.static_doc_dirs)

    # Build Doxygen configuration
    doxygen_build_dir = root_project_dir / '_doxygen'
    doxygen_xml_dir = doxygen_build_dir / 'xml'
    os.makedirs(doxygen_xml_dir, exist_ok=True)
    doxygen_conf = DoxygenConfiguration(xml_output=doxygen_xml_dir)
    for package_name, package in packages.items():
        if package.doxygen_conf_path:
            # Use a doxygen.conf file that is already preprocessed by
            # sconsUtils
            package_doxygen_conf = DoxygenConfiguration.from_doxygen_conf(
                conf_text=package.doxygen_conf_path.read_text(),
                root_dir=package.doxygen_conf_path.parent
            )
        elif package.doxygen_conf_path_in:
            # Fall back to the doxygen.conf.in template file
            package_doxygen_conf = DoxygenConfiguration.from_doxygen_conf(
                conf_text=package.doxygen_conf_in_path.read_text(),
                root_dir=package.doxygen_conf_in_path.parent
            )
            # Add input paths for C++ source directories that are absent
            # in a doxygen.conf.in template
            preprocess_package_doxygen_conf(
                conf=package_doxygen_conf,
                package=package
            )

        else:
            # No Doxygen configuration for this package
            continue

        # Append package's configurations to the root configuration
        doxygen_conf += package_doxygen_conf

    # Trigger Doxygen build
    return_code = run_doxygen(conf=doxygen_conf, root_dir=doxygen_build_dir)

    # Trigger the Sphinx build
    return_code = run_sphinx(root_project_dir)
    return return_code


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
