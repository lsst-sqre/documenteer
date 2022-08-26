import os
import sys
from typing import List

from documenteer import __version__

# General configuration ======================================================

# General information about the project.
project = "Documenteer"
copyright = (
    "2015-2022 "
    "Association of Universities for Research in Astronomy, Inc. (AURA)"
)
author = "Rubin Observatory"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.ifconfig",
    "sphinx_click.ext",
    "sphinxcontrib.autoprogram",
    "sphinx-prompt",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
    "sphinx_automodapi.automodapi",
    "sphinx_automodapi.smart_resolver",
    "documenteer.sphinxext",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".txt": "markdown",
    ".md": "markdown",
}

root_doc = "index"


# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
version = __version__
release = version

language = "en"

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
# today = ''
# Else, today_fmt is used as the format for a strftime call.
# today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ["_build", "README.rst"]

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"

# The reST default role cross-links Python (used for this markup: `text`)
default_role = "py:obj"

# Intersphinx

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "requests": ("https://2.python-requests.org/en/master/", None),
    "developer": ("https://developer.lsst.io/", None),
    "pybtex": ("https://docs.pybtex.org/", None),
    "sphinx": ("http://www.sphinx-doc.org/en/master/", None),
}

# Warnings to ignore
nitpick_ignore = [
    # This link to the base pybtex still never resolves because it is not
    # in pybtex's intersphinx'd API reference.
    ("py:class", "pybtex.style.formatting.plain.Style"),
]

# Options for linkcheck builder ==============================================

linkcheck_retries = 2

# Since Tucson-based IT infrastructure is frequently down
linkcheck_ignore = [
    r"^https://jira.lsstcorp.org/browse/",
    r"^https://ls.st/",
]

linkcheck_timeout = 15

# Options for HTML output ====================================================

html_theme = "pydata_sphinx_theme"

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {"logotext": project}

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = "Documenteer"

# A shorter title for the navigation bar.  Default is the same as html_title.
html_short_title = "Documenteer"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path: List[str] = []

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = False

# Options for the API reference ==============================================

# sphinx_autodoc_typehints
always_document_param_types = True
typehints_defaults = "comma"

# napoleon
napoleon_google_docstring = False  # non-default
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# ReStructuredText epilog for common links/substitutions =====================
rst_epilog = """

.. _conda-forge: https://conda-forge.org
.. _conda: https://conda.io/en/latest/index.html
"""

# My-ST (Markdown) ===========================================================
# https://myst-parser.readthedocs.io/en/latest/syntax/optional.html

myst_enable_extensions = [
    "amsmath",
    "colon_fence",
    "deflist",
    "dollarmath",
    "fieldlist",
    "html_admonition",
    "html_image",
    "linkify",
    "replacements",
    "smartquotes",
    "strikethrough",
    "substitution",
    "tasklist",
]
