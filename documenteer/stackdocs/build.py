"""Stack documentation build system.
"""

from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from builtins import *  # NOQA
from future.standard_library import install_aliases
install_aliases()  # NOQA


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
