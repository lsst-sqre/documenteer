"""Utilities for discovering packages in a stack and discovering attributes
and their documentation.
"""

__all__ = (
    "discover_setup_packages",
    "find_table_file",
    "list_packages_in_eups_table",
    "Package",
    "NoPackageDocs",
    "find_package_docs",
)

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union

import yaml


def discover_setup_packages(
    scope: Optional[List[str]] = None,
) -> Dict[str, Dict[str, str]]:
    """Summarize packages currently set up by EUPS, listing their
    set up directories and EUPS version names.

    Parameters
    ----------
    scope : `list` of `str`
        Names of packages that are in scope to include in the returned package
        data. Leave as `None` if packages should not be filtered.

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

    packages: Dict[str, Dict[str, str]] = {}
    for package in products:
        name = package.name
        if scope is not None and name not in scope:
            logger.debug("Ignoring %s since it is not in scope.", name)
            continue
        info = {"dir": package.dir, "version": package.version}
        packages[name] = info
        logger.debug(
            "Found setup package: %s %s %s", name, info["version"], info["dir"]
        )

    return packages


def find_table_file(root_project_dir: Union[str, Path]) -> Path:
    """Find the EUPS table file for a project.

    Parameters
    ----------
    root_project_dir : `str` or `pathlib.Path`
        Path to the root directory of the main documentation project. This
        is the directory containing the ``conf.py`` file and a ``ups``
        directory.

    Returns
    -------
    table_path : `pathlib.Path`
        Path to the EUPS table file.
    """
    root_project_dir = Path(root_project_dir)
    ups_dir_path = root_project_dir / "ups"
    table_path = None
    for p in ups_dir_path.iterdir():
        if p.suffix == ".table" and p.is_file():
            table_path = p
    if table_path is None:
        raise RuntimeError(
            f"Could not find the EUPS table file for {root_project_dir}"
        )
    return table_path


def list_packages_in_eups_table(table_text: str) -> List[str]:
    """List the names of packages that are required by an EUPS table file.

    Parameters
    ----------
    table_text : `str`
        The text content of an EUPS table file.

    Returns
    -------
    names : `list` of `str`
        List of package names that are required byy the EUPS table file.
    """
    logger = logging.getLogger(__name__)
    # This pattern matches required product names in EUPS table files.
    pattern = re.compile(r"setupRequired\((?P<name>\w+)\)")
    listed_packages = [m.group("name") for m in pattern.finditer(table_text)]
    logger.debug("Packages listed in the table file: %r", listed_packages)
    return listed_packages


@dataclass
class Package:
    """Metadata about a stack package's documentation content."""

    root_dir: Path
    """Root directory path of the package.
    """

    doc_dir: Path
    """Root directory path of the package's ``doc/`` directory.
    """

    package_dirs: Dict[str, Path] = field(default_factory=dict)
    """Package documentation directories.

    Keys are package names (for example, ``'afw'``). Values are absolute
    directory paths to the package's documentation directory inside the
    package's ``doc`` directory. If there is no package-level documentation the
    dictionary is empty.
    """

    module_dirs: Dict[str, Path] = field(default_factory=dict)
    """Module documentation directories.

    Keys are module names (for example, ``'lsst.afw.table'``). Values are
    absolute directory paths to the module's directory inside the package's
    ``doc`` directory. If a package has no modules the dictionary is empty.
    """

    static_doc_dirs: Dict[str, Path] = field(default_factory=dict)
    """Sphinx ``_static/`` content directories.

    Keys are directory names relative to the ``_static`` directory. Values are
    absolute directory paths to the static documentation directory in the
    package. If there isn't a declared ``_static`` directory, this dictionary
    is empty.
    """

    doxygen_conf_path: Optional[Path] = field(default=None)
    """Path to the ``doxygen.conf`` file, which is typically generated by
    ``sconsUtils`` based on the ``doxygen.conf.in`` file, but with additional
    configurations.
    """

    doxygen_conf_in_path: Optional[Path] = field(default=None)
    """Path to the ``doxygen.conf.in`` file, indicating Doxygen documentation
    should be generated.
    """


def find_package_docs(
    package_dir: Union[str, Path], skipped_names: Optional[List[str]] = None
) -> Package:
    """Find documentation directories in a package using ``manifest.yaml``
    and heuristics.

    Parameters
    ----------
    package_dir : `str` or `pathlib.Path`
        Directory of an EUPS package.
    skipped_names : `list` of `str`, optional
        List of package or module names to skip when creating links.

    Returns
    -------
    doc_dirs : `Package`
        Metadata about a stack package's documentation content.

    Raises
    ------
    NoPackageDocs
       Raised when the ``manifest.yaml`` file cannot be found in a package.

    Notes
    -----
    Stack packages have documentation in subdirectories of their ``doc``
    directory. The ``manifest.yaml`` file declares what these directories are
    so that they can be symlinked into the root project.

    There are three types of documentation directories:

    1. Package doc directories contain documentation for the EUPS package
       aspect. This is optional.
    2. Module doc directories contain documentation for a Python package
       aspect. These are optional.
    3. Static doc directories are root directories inside the package's
       ``doc/_static/`` directory. These are optional.

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

    if skipped_names is None:
        skipped_names = []

    package_dir = Path(package_dir)

    package = Package(root_dir=package_dir, doc_dir=package_dir / "doc")

    modules_yaml_path = package.doc_dir / "manifest.yaml"
    if not modules_yaml_path.is_file():
        raise NoPackageDocs(r"Manifest YAML not found: {modules_yaml_path}")

    with open(modules_yaml_path) as f:
        manifest_data = yaml.safe_load(f)

    if "modules" in manifest_data:
        for module_name in manifest_data["modules"]:
            if module_name in skipped_names:
                logger.debug("Skipping module %s", module_name)
                continue
            module_dir = package.doc_dir / module_name

            if not module_dir.is_dir():
                logger.warning("module doc dir not found: %s", module_dir)
                continue

            package.module_dirs[module_name] = module_dir
            logger.debug("Found module doc dir %s", module_dir)

    if "package" in manifest_data:
        package_name = manifest_data["package"]
        if package_name in skipped_names:
            logger.debug("Skipping package %s", package_name)

        full_package_dir = package.doc_dir / package_name

        if full_package_dir.is_dir():
            package.package_dirs[package_name] = full_package_dir
            logger.debug("Found package doc dir %s", full_package_dir)
        else:
            logger.warning("package doc dir not found: %s", full_package_dir)

    if "statics" in manifest_data:
        for static_dirname in manifest_data["statics"]:
            full_static_dir = package.doc_dir / static_dirname

            if not full_static_dir.is_dir():
                logger.warning(
                    "_static doc dir not found: %s", full_static_dir
                )
                continue

            # Make a relative path to `_static` that's used as the
            # link source in the root docproject's _static/ directory
            relative_static_dir = str(
                full_static_dir.relative_to(package.doc_dir / "_static")
            )
            package.static_doc_dirs[relative_static_dir] = full_static_dir
            logger.debug("Found _static doc dir: %s", full_static_dir)

    doxygen_conf_path = package.doc_dir / "doxygen.conf"
    if doxygen_conf_path.is_file():
        package.doxygen_conf_path = doxygen_conf_path

    doxygen_conf_in_path = package.doc_dir / "doxygen.conf.in"
    if doxygen_conf_in_path.is_file():
        package.doxygen_conf_in_path = doxygen_conf_in_path

    return package


class NoPackageDocs(Exception):
    """Exception raised when documentation is not found for an EUPS package."""
