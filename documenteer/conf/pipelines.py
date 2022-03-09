"""Sphinx configuration for lsst/pipelines_lsst_io (pipelines.lsst.io).

To use this configuration in a Sphinx project, write a conf.py::

    from documenteer.conf.pipelines import *

For additional documentation, see:

    https://documenteer.lsst.io/pipelines/configuration.html#pipelines-conf
"""
# This configuration is broken down into these sections:
#
# #EXT
#     Sphinx extensions
# #SPHINX
#     Core Sphinx configurations
# #INTER
#     Intersphinx configuration
# #HTML
#     HTML builder and theme configuration
# #AUTOMODAPI
#     automodapi and autodoc configuration
# #GRAPHVIZ
#     graphviz configuration
# #TODO
#     todo extension configuration
# #EUPS
#     Compute EUPS tag and versioning information
# #JINJA
#     Jinja extension configuration
# #EPILOG
#     rst_epilog is reStructured text content present on every page

__all__ = (
    # EXT
    "extensions",
    # SPHINX
    "project",
    "today",
    "copyright",
    "source_suffix",
    "source_encoding",
    "master_doc",
    "numfig",
    "numfig_format",
    "default_role",
    "exclude_patterns",
    # INTER
    "intersphinx_mapping",
    "intersphinx_timeout",
    "intersphinx_cache_limit",
    # HTML
    "templates_path",
    "html_theme",
    "html_theme_path",
    "html_theme_options",
    "html_title",
    "html_short_title",
    "html_logo",
    "html_favicon",
    "html_static_path",
    "html_last_updated_fmt",
    "html_use_smartypants",
    "html_domain_indices",
    "html_use_index",
    "html_split_index",
    "html_show_sourcelink",
    "html_copy_source",
    "html_show_sphinx",
    "html_show_copyright",
    "html_file_suffix",
    "html_search_language",
    "html_extra_path",
    # AUTOMODAPI
    "numpydoc_show_class_members",
    "autosummary_generate",
    "automodapi_toctreedirnm",
    "automodsumm_inherited_members",
    "autodoc_inherit_docstrings",
    "autoclass_content",
    "autodoc_default_flags",
    # DOXYLINK
    "doxylink",
    "documenteer_autocppapi_doxylink_role",
    # GRAPHVIZ
    "graphviz_output_format",
    "graphviz_dot_args",
    # TODO
    "todo_include_todos",
    # EUPS
    "eups_tag",
    "git_ref",
    # JINJA
    "jinja_contexts",
    # EPILOG
    "rst_epilog",
)

import datetime
import os
from pathlib import Path

import lsst_sphinx_bootstrap_theme

from documenteer.packagemetadata import Semver, get_package_version_semver

# ============================================================================
# #EXT Sphinx extensions
# ============================================================================

# The extension name for sphinx-jinja changed with version 2.0.0
_sphinx_jinja_ext_name = "sphinx_jinja"
try:
    if get_package_version_semver("sphinx-jinja") < Semver.parse("2.0.0"):
        # Use older sphinx jinja name for sphinx-jinja < 2.0.0
        _sphinx_jinja_ext_name = "sphinxcontrib.jinja"
except Exception as e:
    print(f"Error getting sphinx-jinja version: {str(e)}")

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.coverage",
    "sphinx.ext.mathjax",
    "sphinx.ext.ifconfig",
    _sphinx_jinja_ext_name,
    "sphinx-prompt",
    "sphinxcontrib.autoprogram",
    "sphinxcontrib.doxylink",
    "numpydoc",
    "sphinx_automodapi.automodapi",
    "sphinx_automodapi.smart_resolver",
    "documenteer.sphinxext",
    "documenteer.sphinxext.lssttasks",
    "documenteer.ext.autocppapi",
    "documenteer.ext.autodocreset",
    "sphinx_click",
]

# ============================================================================
# #SPHINX Core Sphinx configurations
# ============================================================================
project = "LSST Science Pipelines"

_date = datetime.datetime.now()

today = _date.strftime("%Y-%m-%d")

# Use this copyright for now. Ultimately we want to gather COPYRIGHT files
# and build an integrated copyright that way.
copyright = f"2015-{_date.year} LSST contributors"

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
source_suffix = ".rst"

# The encoding of source files.
source_encoding = "utf-8"

# The master toctree document.
master_doc = "index"

# Configure figure numbering
numfig = True
numfig_format = {
    "figure": "Figure %s",
    "table": "Table %s",
    "code-block": "Listing %s",
}

# The reST default role (used for this markup: `text`)
default_role = "obj"

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = [
    "README.rst",
    # Build products
    "_build",
    # Doxygen build products
    "_doxygen",
    # Source for release notes (contents are included in built pages)
    "releases/note-source/*.rst",
    "releases/tickets-source/*.rst",
    # EUPS configuration directory
    "ups",
    # Recommended directory for pip installing doc eng Python packages
    ".pyvenv",
    # GitHub templates
    ".github",
    # This 'home' directory is created by the docubase image for the
    # sqre/infra/documenteer ci.lsst.codes Jenkins job. Ideally this
    # shouldn't be in the directory at all, but we certainly need to
    # ignore it while its here.
    "home",
    # The configuration files
    "conf.py",
    "manifest.yaml",
    "doxygen.conf",
    "doxygen.conf.in",
    # Doxygen build products from scons (in stack package builds)
    "html",
    "xml",
]

# ============================================================================
# #INTER Intersphinx configuration
# ============================================================================
intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "scipy": ("https://docs.scipy.org/doc/scipy/reference/", None),
    "matplotlib": ("https://matplotlib.org/", None),
    "sklearn": ("https://scikit-learn.org/stable/", None),
    "pandas": ("https://pandas.pydata.org/pandas-docs/stable/", None),
    "astropy": ("https://docs.astropy.org/en/stable/", None),
    "astro_metadata_translator": (
        "https://astro-metadata-translator.lsst.io",
        None,
    ),
    "firefly_client": ("https://firefly-client.lsst.io", None),
}
intersphinx_timeout = 10.0  # seconds
intersphinx_cache_limit = 5  # days


# ============================================================================
# #HTML HTML builder and theme configuration
# ============================================================================

# Use the lsst-sphinx-bootstrap-theme
templates_path = [
    "_templates",
    lsst_sphinx_bootstrap_theme.get_html_templates_path(),
]
html_theme = "lsst_sphinx_bootstrap_theme"
html_theme_path = [lsst_sphinx_bootstrap_theme.get_html_theme_path()]

# Theme options are theme-specific and customize the look and feel of a
# theme further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {"logotext": project}

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = project

# A shorter title for the navigation bar.  Default is the same as
# html_title.
html_short_title = project

# The name of an image file (relative to this directory) to place at the
# top of the sidebar.
html_logo = None

# The name of an image file (within the static path) to use as favicon of
# the docs.  This file should be a Windows icon file (.ico) being 16x16 or
# 32x32 pixels large.
html_favicon = None

# Add any paths that contain custom static files (such as style sheets)
# here, relative to this directory. They are copied after the builtin
# static files, so a file named "default.css" will overwrite the builtin
# "default.css".
if os.path.isdir("_static"):
    html_static_path = ["_static"]
else:
    # If a project does not have a _static/ directory, don't list it
    # so that there isn't a warning.
    html_static_path = []

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
html_extra_path = []
if os.path.exists("_doxygen/html"):
    html_extra_path.append("_doxygen/html")

# If not '', a 'Last updated on:' timestamp is inserted at every page
# bottom, using the given strftime format.
html_last_updated_fmt = "%b %d, %Y"

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
html_use_smartypants = True

# If false, no module index is generated.
html_domain_indices = True

# If false, no index is generated.
html_use_index = True

# If true, the index is split into individual pages for each letter.
html_split_index = False

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = False

# Do not copy reST source for each page into the build
html_copy_source = False

# If true, "Created using Sphinx" is shown in the HTML footer. Default is
# True.
html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is
# True.
html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages
# will contain a <link> tag referring to it.  The value of this option must
# be the base URL from which the finished HTML is served.
# html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
html_file_suffix = ".html"

# Language to be used for generating the HTML full-text search index.
html_search_language = "en"

# ============================================================================
# #AUTOMODAPI automodapi and autodoc configuration
# ============================================================================
# Don't show summaries of the members in each class along with the
# class' docstring
numpydoc_show_class_members = False

autosummary_generate = True

automodapi_toctreedirnm = "py-api"
automodsumm_inherited_members = True

# Docstrings for classes and methods are inherited from parents.
autodoc_inherit_docstrings = True

# Class documentation should only contain the class docstring and
# ignore the __init__ docstring, account to LSST coding standards.
# c['autoclass_content'] = "both"
autoclass_content = "class"

# Default flags for automodapi directives. Special members are dunder
# methods.
# NOTE: We want to used `inherited-members`, but it seems to be causing
# documentation duplication in the automodapi listings. We're leaving
# this out for now. See https://jira.lsstcorp.org/browse/DM-14782 for
# additional notes.
# NOTE: Without inherited members set, special-members doesn't need seem
# to have an effect (even for special members where the docstrings are
# directly written in the class, not inherited.
# autodoc_default_flags = ['inherited-members']
autodoc_default_flags = ["show-inheritance", "special-members"]

# ============================================================================
# #DOXYLINK Doxylink configuration
# ============================================================================
tag_path = Path(".").joinpath("_doxygen", "doxygen.tag")
if tag_path.exists():
    doxylink = {"lsstcc": (str(tag_path), "cpp-api")}
else:
    doxylink = {}

documenteer_autocppapi_doxylink_role = "lsstcc"

# ============================================================================
# #GRAPHVIZ graphviz configuration
# graphviz is primarily used by automodapi to create inheritance diagrams.
# ============================================================================
# Render inheritance diagrams in SVG
graphviz_output_format = "svg"

graphviz_dot_args = [
    "-Nfontsize=10",
    "-Nfontname=Helvetica Neue, Helvetica, Arial, sans-serif",
    "-Efontsize=10",
    "-Efontname=Helvetica Neue, Helvetica, Arial, sans-serif",
    "-Gfontsize=10",
    "-Gfontname=Helvetica Neue, Helvetica, Arial, sans-serif",
]

# ============================================================================
# #TODO todo extension configuration
# ============================================================================
# Hide todo directives in the "published" documentation on the main site.
todo_include_todos = False

# ============================================================================
# #EUPS
# Compute information about the EUPS tag and versioning
# This info will get exposed through the Jinja configuration and the rst prolog
# ============================================================================
# Attempt to get the EUPS tag from the build environment
eups_tag = os.getenv("EUPS_TAG", "d_latest")

# Try to guess the Git ref that corresponds to this tag
if eups_tag in ("d_latest", "w_latest", "current"):
    git_ref = "master"
elif eups_tag.startswith("d_"):
    # Daily EUPS tags are not tagged on git
    git_ref = "master"
elif eups_tag.startswith("v"):
    # Major version or release candidate tag
    git_ref = eups_tag.lstrip("v").replace("_", ".")
elif eups_tag.startswith("w_"):
    # Regular weekly tag
    git_ref = eups_tag.replace("_", ".")
else:
    # Ideally shouldn't get to this point
    git_ref = "master"

# ============================================================================
# #JINJA jinja extension configuration
# ============================================================================
jinja_contexts = {
    "default": {
        "release_eups_tag": eups_tag,
        "release_git_ref": git_ref,
        "pipelines_demo_ref": git_ref,
        "scipipe_conda_ref": git_ref,
        "newinstall_ref": git_ref,
    }
}

# ============================================================================
# rst_epilog is reStructured text content present on every page
# ============================================================================
rst_epilog = f"""

.. |eups-tag| replace:: {eups_tag}
.. |eups-tag-mono| replace:: ``{eups_tag}``
.. |eups-tag-bold| replace:: **{eups_tag}**
"""
