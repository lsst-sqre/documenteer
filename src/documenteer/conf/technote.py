"""Sphinx configuration for LSST technotes.

To use this configuration in a Sphinx technote project, write a conf.py
containing::

    from documenteer.conf.technote import *
"""

# This configuration is broken down into these sections:
#
# #METADATA
#     Configurations based on metadata.yaml
# #EXT
#     Sphinx extensions
# #SPHINX
#     Core Sphinx configurations
# #HTML
#     HTML builder and theme configuration
# #TODO
#     todo extension configuration
# #MATHJAX
#     MathJax extension configuration
# #INTER
#     Intersphinx configuration

# Ordered as they are declared in this module
__all__ = (
    # METADATA
    "project",
    "authors",
    "copyright",
    "exclude_patterns",
    "version",
    "release",
    "today",
    "html_context",
    # EXT
    "extensions",
    # SPHINX
    "source_suffix",
    "source_encoding",
    "master_doc",
    "numfig",
    "numfig_format",
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
    "html_extra_path",
    "html_last_updated_fmt",
    "html_use_smartypants",
    "html_domain_indices",
    "html_use_index",
    "html_split_index",
    "html_show_sourcelink",
    "html_show_sphinx",
    "html_file_suffix",
    "html_search_language",
    # TODO
    "todo_include_todos",
    # MATHJAX
    "mathjax_path",
    # INTER
    "intersphinx_mapping",
    "intersphinx_timeout",
    "intersphinx_cache_limit",
    # BIBTEX
    "bibtex_bibfiles",
    "bibtex_default_style",
)

import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import lsst_dd_rtd_theme
import yaml

from documenteer.sphinxconfig.utils import (
    get_project_content_commit_date,
    read_git_branch,
)

# ============================================================================
# #METADATA Configurations based on metadata.yaml
# ============================================================================

_metadata_path = Path("metadata.yaml")
try:
    with _metadata_path.open() as fp:
        _metadata = yaml.safe_load(fp)
except OSError:
    raise OSError(
        "Technotes require a metadata.yaml file for configuration, but one"
        "couldn't be opened. See the technote template at "
        "https://github.com/lsst/templates/tree/master/project_templates/"
        "technote_rst"
    )

project = f'{_metadata["doc_id"]}: {_metadata["doc_title"]}'

# FIXME Ideally we want to use an oxford comma here.
authors = ", ".join(_metadata["authors"])

copyright = _metadata["copyright"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = _metadata.get("exclude_patterns", ["_build", "README.rst"])

try:
    version = read_git_branch()
    _git_branch = version
except Exception as e:
    print("Caught exception: {}".format(e))
    print("Cannot get Git branch information.")
    # defaults
    version = "Unknown"
    _git_branch = "master"

# Override version with metadata.yaml
if "version" in _metadata:
    version = _metadata["version"]

# The edit_url is used for "Edit on GitHub" functionality
_github_url: Optional[str]
_edit_url: Optional[str]
if "github_url" in _metadata:
    _github_url = _metadata["github_url"]
else:
    _github_url = None
if _github_url is not None:
    if not _github_url.endswith("/"):
        _github_url = _github_url + "/"
    _edit_url = f"{_github_url}blob/{_git_branch}/index.rst"
else:
    _github_url = None
    _edit_url = None

# The full version, including alpha/beta/rc tags.
if "dev_version_suffix" in _metadata:
    release = "{version}{_metadata['dev_version_suffix']}"
else:
    release = version

if "last_revised" in _metadata:
    _date = datetime.datetime.strptime(_metadata["last_revised"], "%Y-%m-%d")
else:
    # obain date from Git commit at most recent content commit since HEAD
    try:
        _date = get_project_content_commit_date(exclusions=exclude_patterns)
    except Exception as e:
        print("Caught exception: {}".format(e))
        print("Cannot get project content git commit date.")
        _date = datetime.datetime.now()
today = _date.strftime("%Y-%m-%d")

# This is available to Jinja2 templates
html_context = {
    "author_list": _metadata["authors"],
    "doc_id": _metadata["doc_id"],
    "doc_title": _metadata["doc_title"],
    "last_revised": today,
    "git_branch": _git_branch,
    "github_url": _github_url,
    "edit_url": _edit_url,
}

# ============================================================================
# #EXT Sphinx extensions
# ============================================================================
extensions = [
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.mathjax",
    "sphinx.ext.ifconfig",
    "sphinx-prompt",
    "sphinxcontrib.bibtex",
    "documenteer.sphinxext",
    "documenteer.sphinxext.bibtex",
]

# ============================================================================
# #SPHINX Core Sphinx configurations
# ============================================================================
# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
source_suffix = ".rst"

# The encoding of source files.
source_encoding = "utf-8"

# The master toctree document.
master_doc = "index"

numfig = True
numfig_format = {
    "figure": "Figure %s",
    "table": "Table %s",
    "code-block": "Listing %s",
}

# ============================================================================
# #HTML HTML builder and theme configuration
# ============================================================================
templates_path = ["_templates"]
html_theme = "lsst_dd_rtd_theme"
html_theme_path = [lsst_dd_rtd_theme.get_html_theme_path()]

# Theme options are theme-specific and customize the look and feel of a
# theme further.  For a list of options available for each theme, see the
# documentation.
html_theme_options: Dict[str, Any] = {}

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = project

# A shorter title for the navigation bar.  Default is the same as
# html_title.
html_short_title = _metadata["doc_id"]

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
if Path("_static").is_dir():
    html_static_path = ["_static"]
else:
    # If a project does not have a _static/ directory, don't list it
    # so that there isn't a warning.
    html_static_path = []

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
html_extra_path: List[str] = []

# If not '', a 'Last updated on:' timestamp is inserted at every page
# bottom, using the given strftime format.
html_last_updated_fmt = "%b %d, %Y"

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
html_use_smartypants = True

# If false, no module index is generated.
html_domain_indices = False

# If false, no index is generated.
html_use_index = False

# If true, the index is split into individual pages for each letter.
html_split_index = False

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
html_show_copyright = True

# This is the file name suffix for HTML files (e.g. ".xhtml").
html_file_suffix = ".html"

# Language to be used for generating the HTML full-text search index.
html_search_language = "en"

# ============================================================================
# #TODO todo extension configuration
# ============================================================================
todo_include_todos = True

# ============================================================================
# #MATHJAX MathJax extension configuration
# ============================================================================
# http://docs.mathjax.org/en/v2.7-latest/start.html#using-a-content-delivery-network-cdn
mathjax_path = (
    "https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.5/"
    "MathJax.js?config=default"
)

# ============================================================================
# #INTER Intersphinx configuration
# ============================================================================
intersphinx_mapping: Dict[str, Tuple[Union[str, None]]] = {}
intersphinx_timeout = 10.0  # seconds
intersphinx_cache_limit = 5  # days

# ============================================================================
# #BIBTEX sphinxcontrib-bibtex configuration
# ============================================================================
bibtex_bibfiles = []
if Path("local.bib").exists():
    bibtex_bibfiles.append("local.bib")
for path in Path("lsstbib").glob("*.bib"):
    bibtex_bibfiles.append(str(path))

bibtex_default_style = "lsst_aa"
