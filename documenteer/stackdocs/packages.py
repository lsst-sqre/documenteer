# encoding: utf-8
"""Utilities for working with eups-based stack packages.

Use :func:`list_packages` to get a `dict` of available packages in the Stack.
"""

from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future.utils import raise_with_traceback

import os

import eups


def get_lsstsw_build_dir():
    """Get path to the ``lsstsw/build`` directory.

    Returns
    -------
    lsstsw_build_dir : str
        Path to the ``lsstsw/build`` directory

    Raises
    ------
    RuntimeError
        If ``$LSSTSW_BUILD_DIR`` was not set when the default lsstsw location
        is not valid (``~/lsstsw``).
    """
    default = os.path.expandvars('$HOME/lsstsw')
    lsstsw_build_dir = os.getenv('LSSTSW_BUILD_DIR', default)
    if not os.path.exists(lsstsw_build_dir):
        message = '$LSSTSW_BUILD_DIR is not set'
        raise_with_traceback(RuntimeError(message))
    return lsstsw_build_dir


def list_packages(eups_env=None):
    """Discover all packages in the stack.

    Attempts to do something like the the printProducts function in Eups:
    https://github.com/RobertLuptonTheGood/eups/blob/master/python/eups/app.py
    However, the function currently uses repos.yaml, and thus is tied to
    the packages that are available in lsstsw.

    Parameters
    ----------
    eups_env : :class:`eups.Eups` instance, optional
        The Eups environment. This function must be run from an enviroment
        where Eups is setup.

    Returns
    -------
    packages : dict
        A `dict` of :class:`Package` instances representing each Stack package,
        keyed by package name.
    """
    if eups_env is None:
        eups_env = eups.Eups()
    product_list = eups_env.findProducts(None, None, None)
    # The set of product names available (remove duplicate versions)
    product_names = list(set([p.name for p in product_list]))

    packages = {}
    for name in product_names:
        pkg = Package(name, eups_env)
        packages[name] = pkg

    return packages


class Package(object):
    """A stack package in the lsstsw build system.

    Attributes
    ----------
    name : str
        Package's name.

    Parameters
    ----------
    name : str
        Name of the package (i.e., name of the git repo)
    eups_env : :class:`eups.Eups` instance
        The Eups environment. Requires that Eups is setup in the environment.
    """
    def __init__(self, name, eups_env):
        super(Package, self).__init__()
        self.name = name
        self._eups_env = eups_env

    @property
    def repo_path(self):
        """Absolute path to package's checked-out git repo.

        Returns
        -------
        p : str
            Absolute path to the package's checked-out git repository.

        Raises
        ------
        RuntimeError
            If ``$LSSTSW_BUILD_DIR`` was not set when the default lsstsw
            location is not valid (``~/lsstsw``).
        OSError
            If the repository directory does not exist.
        """
        p = os.path.join(get_lsstsw_build_dir(), self.name)
        if not os.path.exists(p):
            raise_with_traceback(
                OSError('{0} not found at {1}'.format(self.name, p)))
        return p

    @property
    def doc_path(self):
        """Absolute path to the package's doc directory.

        Returns
        -------
        p : str
            Absolute path to the package's checked-out doc directory.

        Raises
        ------
        RuntimeError
            If ``$LSSTSW_BUILD_DIR`` was not set when the default lsstsw
            location is not valid (``~/lsstsw``).
        OSError
            If the doc/xml directory does not exist.
        """
        p = os.path.join(self.repo_path, 'doc')
        if not os.path.exists(p):
            raise_with_traceback(
                OSError('{0} does not have a doc directory at {1}'.format(
                    self.name, p)))
        return p

    @property
    def xml_path(self):
        """Absolute path to the package's doc/xml directory where Doxygen-
        created XML is built.

        Returns
        -------
        p : str
            Absolute path to the package's checked-out doc/xml directory.

        Raises
        ------
        RuntimeError
            If ``$LSSTSW_BUILD_DIR`` was not set when the default lsstsw
            location is not valid (``~/lsstsw``).
        OSError
            If the doc/xml directory does not exist.
        """
        p = os.path.join(self.doc_path, 'xml')
        if not os.path.exists(p):
            raise_with_traceback(
                OSError('{0} does not have a doc directory at {1}'.format(
                    self.name, p)))
        return p

    @property
    def eups_version(self):
        """Version of the package as setup by Eups."""
        eups_product = self._eups_env.findProduct('sconsUtils')
        return eups_product.version
