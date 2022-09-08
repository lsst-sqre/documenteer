"""Stack documentation build system.
"""

__all__ = ("build_stack_docs",)

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Union

from ..sphinxrunner import run_sphinx
from .doxygen import (
    DoxygenConfiguration,
    get_doxygen_default_conf_path,
    preprocess_package_doxygen_conf,
    render_doxygen_mainpage,
    run_doxygen,
)
from .pkgdiscovery import (
    NoPackageDocs,
    Package,
    discover_setup_packages,
    find_package_docs,
    find_table_file,
    list_packages_in_eups_table,
)


def build_stack_docs(
    root_project_dir: Union[Path, str],
    skipped_names: Optional[List[str]] = None,
    skippedNames: Optional[List[str]] = None,
    doxygen_conf_defaults_path: Optional[Path] = None,
    prefer_doxygen_conf_in: bool = True,
    enable_doxygen_conf: bool = True,
    enable_doxygen: bool = True,
    enable_package_links: bool = True,
    enable_sphinx: bool = True,
    select_doxygen_packages: Optional[List[str]] = None,
    skip_doxygen_packages: Optional[List[str]] = None,
) -> int:
    """Build stack Sphinx documentation (main entrypoint).

    Parameters
    ----------
    root_project_dir
        Path to the root directory of the main documentation project. This
        is the directory containing the ``conf.py`` file.
    skipped_names
        Optional list of packages to skip while creating symlinks.
    skippedNames
        Old name for the ``skipped_names`` parameter.
    doxygen_conf_defaults_path : `pathlib.Path`
        Path to a Doxygen configuration file that will be referenced from
        the primary Doxygen configuration using the ``@INCLUDE_PATH`` tag. By
        default the Doxygen defaults built into Documenteer are used.
    prefer_doxygen_conf_in
        Prefer using doxygen.conf.in files as the basis for package's Doxygen
        configuration. This mode is useful when building stack documentation
        from a binary distribution of the Stack since the paths in each
        package's ``doxygen.conf`` file refer to paths on the build server.
    enable_doxygen_conf
        Enable building the configuration for the Doxygen build.
    enable_doxygen
        Enable the Doxygen build. If enabled, ``enable_doxygen_conf`` is
        automatically enabled.
    enable_package_links
        Enable linking the documentation directories of individual packages
        into the root documentation directory.
    enable_sphinx
        Enable the Sphinx build. If enabled, ``enable_package_links`` is
        automatically enabled.
    select_doxygen_packages
        If set, only EUPS packages named in this sequence will be processed by
        Doxygen. Packages still need to be set up and have ``doxygen.conf.in``
        files.
    skip_doxygen_packages
        If set, EUPS packages named in this sequence will be removed from the
        set of packages processed by Doxygen.

    Returns
    -------
    sphinx_status : `int`
        The shell status code for the Sphinx build. If ``enable_sphinx`` is
        ``False``, the status defaults to ``0``.
    """
    logger = logging.getLogger(__name__)

    # Reconcile arguments
    root_project_dir = Path(root_project_dir)

    if skipped_names is None:
        skipped_names = skippedNames  # fall back to old name

    if enable_doxygen:
        enable_doxygen_conf = True

    if enable_sphinx:
        enable_package_links = True

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
                package_info["dir"], skipped_names=skipped_names
            )
            packages[package_name] = package_docs
        except NoPackageDocs as e:
            logger.debug(
                "No documentation content found for %s (skipping).\n%s",
                package_name,
                e,
            )
            continue

    if enable_package_links:
        # Create the directory where module content is symlinked
        # NOTE: this path is hard-wired in for pipelines.lsst.io, but could be
        # refactored as a configuration.
        root_modules_dir = os.path.join(root_project_dir, "modules")
        if os.path.isdir(root_modules_dir):
            logger.info("Deleting any existing modules/ symlinks")
            remove_existing_links(root_modules_dir)
        else:
            logger.info("Creating modules/ dir at %s", root_modules_dir)
            os.makedirs(root_modules_dir)

        # Create directory for package content
        root_packages_dir = os.path.join(root_project_dir, "packages")
        if os.path.isdir(root_packages_dir):
            # Clear out existing module links
            logger.info("Deleting any existing packages/ symlinks")
            remove_existing_links(root_packages_dir)
        else:
            logger.info("Creating packages/ dir at %s", root_packages_dir)
            os.makedirs(root_packages_dir)

        # Ensure _static directory exists (but do not delete any existing
        # directory contents)
        root_static_dir = os.path.join(root_project_dir, "_static")
        if os.path.isdir(root_static_dir):
            # Clear out existing directory links
            logger.info("Deleting any existing _static/ symlinks")
            remove_existing_links(root_static_dir)
        else:
            logger.info("Creating _static/ at {0}".format(root_static_dir))
            os.makedirs(root_static_dir)

        # Link to documentation directories of packages from the root project
        for package_name, package in packages.items():
            link_directories(root_modules_dir, package.module_dirs)
            link_directories(root_packages_dir, package.package_dirs)
            link_directories(root_static_dir, package.static_doc_dirs)

    if enable_doxygen_conf:
        doxygen_build_dir = root_project_dir / "_doxygen"
        doxygen_xml_dir = doxygen_build_dir / "xml"
        os.makedirs(doxygen_xml_dir, exist_ok=True)
        doxygen_conf = DoxygenConfiguration()
        doxygen_packages = set(packages.keys())
        if (
            select_doxygen_packages is not None
            and len(select_doxygen_packages) > 0
        ):
            doxygen_packages.intersection_update(select_doxygen_packages)
        if (
            skip_doxygen_packages is not None
            and len(skip_doxygen_packages) > 0
        ):
            doxygen_packages.difference_update(skip_doxygen_packages)
        for package_name in doxygen_packages:
            package = packages[package_name]
            if package.doxygen_conf_path and not prefer_doxygen_conf_in:
                # Use a doxygen.conf file that is already preprocessed by
                # sconsUtils
                package_doxygen_conf = DoxygenConfiguration.from_doxygen_conf(
                    conf_text=package.doxygen_conf_path.read_text(),
                    root_dir=package.doxygen_conf_path.parent,
                )
            elif package.doxygen_conf_in_path:
                # Fall back to the doxygen.conf.in template file
                package_doxygen_conf = DoxygenConfiguration.from_doxygen_conf(
                    conf_text=package.doxygen_conf_in_path.read_text(),
                    root_dir=package.doxygen_conf_in_path.parent,
                )
                # Add input paths for C++ source directories that are absent
                # in a doxygen.conf.in template
                preprocess_package_doxygen_conf(
                    conf=package_doxygen_conf, package=package
                )

            else:
                # No Doxygen configuration for this package
                continue

            # Append package's configurations to the root configuration
            doxygen_conf += package_doxygen_conf

        # Add the mainpage.dox to the build
        mainpage = render_doxygen_mainpage()
        mainpage_path = doxygen_build_dir / "mainpage.dox"
        mainpage_path.write_text(mainpage)
        doxygen_conf.inputs.append(mainpage_path)

        # General configuration of outputs and paths
        doxygen_conf.xml_output = doxygen_xml_dir
        doxygen_conf.tagfile = doxygen_build_dir / "doxygen.tag"
        doxygen_conf.generate_html = True
        doxygen_conf.output_directory = doxygen_build_dir
        doxygen_conf.html_output = doxygen_build_dir / "html" / "cpp-api"
        if doxygen_conf_defaults_path is not None:
            doxygen_conf.include_paths.append(doxygen_conf_defaults_path)
        else:
            doxygen_conf.include_paths.append(get_doxygen_default_conf_path())

        # Pre-create the html/cpp-api directory since Doxygen can't; we want
        # this directory structure to let Sphinx copy the entirety of cpp-api
        # to the output directory.
        os.makedirs(doxygen_conf.html_output, exist_ok=True)

        if enable_doxygen:
            run_doxygen(conf=doxygen_conf, root_dir=doxygen_build_dir)
        else:
            # Write the doxygen configuration for debugging
            doxygen_conf_path = doxygen_build_dir / "doxygen.conf"
            doxygen_conf_path.write_text(doxygen_conf.render())

    # Trigger the Sphinx build
    if enable_sphinx:
        return run_sphinx(root_project_dir)
    else:
        return 0


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

        message = "Linking {0} -> {1}".format(link_name, source_dirname)
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
            logger.debug("Deleting existing symlink {0}".format(full_name))
            os.remove(full_name)
