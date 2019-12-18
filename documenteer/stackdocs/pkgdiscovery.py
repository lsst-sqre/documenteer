"""Utilities for discovering packages in a stack and discovering attributes
and their documentation.
"""

__all__ = ('Package', 'NoPackageDocs', 'find_package_docs')

from dataclasses import dataclass, field
import logging
from pathlib import Path
from typing import Dict, List, Optional

import yaml


@dataclass
class Package:
    """Metadata about a stack package's documentation content.
    """

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
    """Path to the ``doxygen.conf.in`` file, indicating Doxygen documentation
    should be generated.
    """


def find_package_docs(
        package_dir: Path,
        skipped_names: Optional[List[str]] = None) -> Package:
    """Find documentation directories in a package using ``manifest.yaml``
    and heuristics.

    Parameters
    ----------
    package_dir
        Directory of an EUPS package.
    skipped_names
        List of package or module names to skip when creating links.

    Returns
    -------
    doc_dirs
        Metadata about a stack package's documentation content.

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

    package = Package(
        root_dir=package_dir,
        doc_dir=package_dir / 'doc')

    modules_yaml_path = package.doc_dir / 'manifest.yaml'
    if not modules_yaml_path.is_file():
        raise NoPackageDocs(
            r'Manifest YAML not found: {modules_yaml_path}')

    with open(modules_yaml_path) as f:
        manifest_data = yaml.safe_load(f)

    if 'modules' in manifest_data:
        for module_name in manifest_data['modules']:
            if module_name in skipped_names:
                logger.debug('Skipping module %s', module_name)
                continue
            module_dir = package.doc_dir / module_name

            if not module_dir.is_dir():
                logger.warning(
                    'module doc dir not found: %s',
                    module_dir)
                continue

            package.module_dirs[module_name] = module_dir
            logger.debug('Found module doc dir %s', module_dir)

    if 'package' in manifest_data:
        package_name = manifest_data['package']
        if package_name in skipped_names:
            logger.debug('Skipping package %s', package_name)

        full_package_dir = package.doc_dir / package_name

        if full_package_dir.is_dir():
            package.package_dirs[package_name] = full_package_dir
            logger.debug('Found package doc dir %s', full_package_dir)
        else:
            logger.warning('package doc dir not found: %s', full_package_dir)

    if 'statics' in manifest_data:
        for static_dirname in manifest_data['statics']:
            full_static_dir = package.doc_dir / static_dirname

            if not full_static_dir.is_dir():
                logger.warning(
                    '_static doc dir not found: %s', full_static_dir)
                continue

            # Make a relative path to `_static` that's used as the
            # link source in the root docproject's _static/ directory
            relative_static_dir = str(
                full_static_dir.relative_to(package.doc_dir / '_static')
            )
            package.static_doc_dirs[relative_static_dir] = full_static_dir
            logger.debug('Found _static doc dir: %s', full_static_dir)

    return package


class NoPackageDocs(Exception):
    """Exception raised when documentation is not found for an EUPS package.
    """
