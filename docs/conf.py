from importlib.metadata import version as get_version

from documenteer.conf.guide import *

# General information about the project.
copyright = (
    "2015-2022 "
    "Association of Universities for Research in Astronomy, Inc. (AURA)"
)

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
version = get_version("documenteer")
release = version

# Intersphinx

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "requests": ("https://requests.readthedocs.io/en/latest/", None),
    "developer": ("https://developer.lsst.io/", None),
    "pybtex": ("https://docs.pybtex.org/", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
}

# Warnings to ignore
nitpick_ignore = [
    # This link to the base pybtex still never resolves because it is not
    # in pybtex's intersphinx'd API reference.
    ("py:class", "pybtex.style.formatting.plain.Style"),
]

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options["icon_links"][0][
    "url"
] = "https://github.com/lsst-sqre/documenteer"

# Automodapi
# https://sphinx-automodapi.readthedocs.io/en/latest/automodapi.html
automodapi_toctreedirnm = "dev/api/contents"

# ReStructuredText epilog for common links/substitutions =====================
rst_epilog = """

.. _conda-forge: https://conda-forge.org
.. _conda: https://conda.io/en/latest/index.html
"""
