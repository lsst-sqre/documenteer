"""Sphinx configuration for Rubin Observatory User Guides.

To use this configuration in a Sphinx technote project, write a conf.py
containing::

    from documenteer.conf.guide import *
"""

from typing import Any, Dict, List, Tuple, Union

from documenteer.conf import (
    DocumenteerConfig,
    get_asset_path,
    get_template_dir,
)

# This configuration is broken down into these sections:
#
# #EXT
#     Sphinx extensions
# #SPHINX
#     Core Sphinx configurations
# #INTER
#     Intersphinx configuration
# #LINKCHECK
#     Linkcheck builder configuration
# #HTML
#     HTML builder and theme configuration
# #API
#     API reference configuration
# #MYST
#     My-ST markdown configurations


# Ordered as they are declared in this module
__all__ = [
    # EXT
    "extensions",
    # SPHINX
    "project",
    "author",
    "source_suffix",
    "root_doc",
    "language",
    "exclude_patterns",
    "default_role",
    "nitpick_ignore",
    "templates_path",
    # INTER
    "intersphinx_mapping",
    "intersphinx_timeout",
    "intersphinx_cache_limit",
    # LINKCHECK
    "linkcheck_retries",
    "linkcheck_ignore",
    "linkcheck_timeout",
    # HTML
    "html_theme",
    "html_theme_options",
    "html_sidebars",
    "html_title",
    "html_short_title",
    "html_static_path",
    "html_css_files",
    "html_show_sourcelink",
    # API
    "automodapi_toctreedirnm",
    "always_document_param_types",
    "typehints_defaults",
    "napoleon_google_docstring",
    "napoleon_numpy_docstring",
    "napoleon_include_init_with_doc",
    "napoleon_include_private_with_doc",
    "napoleon_include_special_with_doc",
    "napoleon_use_admonition_for_examples",
    "napoleon_use_admonition_for_notes",
    "napoleon_use_admonition_for_references",
    "napoleon_use_ivar",
    "napoleon_use_param",
    "napoleon_use_rtype",
    "napoleon_preprocess_types",
    "napoleon_type_aliases",
    "napoleon_attr_annotations",
    # MYST
    "myst_enable_extensions",
]

_conf = DocumenteerConfig.find_and_load()


# ============================================================================
# #EXT Sphinx extensions
# ============================================================================

extensions = [
    "myst_parser",
    "sphinx_design",
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

# ============================================================================
# #SPHINX Core Sphinx configurations
# ============================================================================

project = _conf.project

author = "Rubin Observatory"

source_suffix = {
    ".rst": "restructuredtext",
    ".txt": "markdown",
    ".md": "markdown",
}

root_doc = "index"

language = "en"

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ["_build", "README.rst", "README.md"]

# The reST default role cross-links Python (used for this markup: `text`)
default_role = "py:obj"

# Warnings to ignore
nitpick_ignore: List[Tuple[str, str]] = []

# A list of paths that contain extra templates (or templates that overwrite
# builtin/theme-specific templates).
templates_path = [get_template_dir("pydata")]

# ============================================================================
# #INTER Intersphinx configuration
# ============================================================================

# Example entry:
#   "python": ("https://docs.python.org/3/", None),
intersphinx_mapping: Dict[str, Tuple[Union[str, None]]] = {}

intersphinx_timeout = 10.0  # seconds

intersphinx_cache_limit = 5  # days


# ============================================================================
# #LINKCHECK Linkcheck builder configuration
# ============================================================================

linkcheck_retries = 2

# Tucson IT infrastructure sometimes goes down or has TLS issues
linkcheck_ignore = [
    r"^https://jira.lsstcorp.org/browse/",
    r"^https://ls.st/",
]

linkcheck_timeout = 15

# ============================================================================
# #HTML HTML builder and theme configuration
# ============================================================================

html_theme = "pydata_sphinx_theme"

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
    "header_links_before_dropdown": 5,
    "external_links": [{"name": "Rubin docs", "url": "https://www.lsst.io"}],
    "icon_links": [
        {
            "name": "GitHub",
            # "url": "https://github.com/lsst-sqre/documenteer",
            "icon": "fab fa-github-square",
            "type": "fontawesome",
        }
    ],
    "logo": {
        "image_light": "rubin-titlebar-imagotype-light.svg",
        "image_dark": "rubin-titlebar-imagotype-dark.svg",
        "text": project,
    },
    "favicons": [
        {
            "rel": "icon",
            "sizes": "32x32",
            "href": "rubin-favicon-transparent-32px.png",
        },
        {"rel": "icon", "href": "rubin-favicon.svg"},
    ],
    "pygment_light_style": "xcode",
    "pygment_dark_style": "github-dark",
}

# in pydata-sphinx-theme 0.10.0 it'll be possible to use
# :html_theme.sidebar_secondary.remove: metadata to remove the sidebar
# for a specific page instead
html_sidebars: Dict[str, List[Any]] = {"index": [], "changelog": []}

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = project

# A shorter title for the navigation bar.  Default is the same as html_title.
html_short_title = project

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path: List[str] = [
    get_asset_path("rubin-titlebar-imagotype-dark.svg"),
    get_asset_path("rubin-titlebar-imagotype-light.svg"),
    get_asset_path("rubin-favicon-transparent-32px.png"),
    get_asset_path("rubin-favicon.svg"),
    get_asset_path("rubin-pydata-theme.css"),
]

html_css_files = ["rubin-pydata-theme.css"]

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = False

# ============================================================================
# #API API reference configurations
# ============================================================================

# Automodapi
# https://sphinx-automodapi.readthedocs.io/en/latest/automodapi.html
automodapi_toctreedirnm = "api"

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


# ============================================================================
# #MYST My-ST markdown configurations
# https://myst-parser.readthedocs.io/en/latest/syntax/optional.html
# ============================================================================

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
