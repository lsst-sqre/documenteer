"""Sphinx configuration for lsst/pipelines_lsst_io (pipelines.lsst.io).

To use this configuration in a Sphinx project, write a conf.py::

    from documenteer.conf.pipelines import *

For additional documentation, see:

    https://documenteer.lsst.io/pipelines/configuration.html#pipelines-conf
"""

import datetime
import os
from pathlib import Path

# Use Rubin Guides as the base theme
from .guide import *  # noqa: F403

# ============================================================================
# #EXT Sphinx extensions
# ============================================================================


extensions.extend(  # noqa: F405
    [
        "sphinxcontrib.autoprogram",
        "sphinxcontrib.doxylink",
        "documenteer.ext.packagetoctree",
        "documenteer.ext.lssttasks",
        "documenteer.ext.autocppapi",
        "documenteer.ext.autodocreset",
        "sphinx_click",
    ]
)

# ============================================================================
# #SPHINX Core Sphinx configurations
# ============================================================================
project = "LSST Science Pipelines"

_date = datetime.datetime.now()

today = _date.strftime("%Y-%m-%d")

# Use this copyright for now. Ultimately we want to gather COPYRIGHT files
# and build an integrated copyright that way.
copyright = f"2015-{_date.year} Rubin Observatory"

# Configure figure numbering
numfig = True
numfig_format = {
    "figure": "Figure %s",
    "table": "Table %s",
    "code-block": "Listing %s",
}

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns.extend(  # noqa: F405
    [
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
)

# ============================================================================
# #INTER Intersphinx configuration
# ============================================================================
intersphinx_mapping.update(  # noqa: F405
    {
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
)
intersphinx_timeout = 10.0  # seconds
intersphinx_cache_limit = 5  # days


# ============================================================================
# #HTML HTML builder and theme configuration
# ============================================================================

# Add any paths that contain custom static files (such as style sheets)
# here, relative to this directory. They are copied after the builtin
# static files, so a file named "default.css" will overwrite the builtin
# "default.css".
if os.path.isdir("_static"):
    html_static_path.append("_static")  # noqa: F405

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
html_extra_path = []
if os.path.exists("_doxygen/html"):
    html_extra_path.append("_doxygen/html")

# ============================================================================
# #AUTOMODAPI automodapi, autodoc and napoleon configuration
# ============================================================================

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
    git_ref = "main"
elif eups_tag.startswith("d_"):
    # Daily EUPS tags are not tagged on git
    git_ref = "main"
elif eups_tag.startswith("v"):
    # Major version or release candidate tag
    git_ref = eups_tag.lstrip("v").replace("_", ".")
elif eups_tag.startswith("w_"):
    # Regular weekly tag
    git_ref = eups_tag.replace("_", ".")
else:
    # Ideally shouldn't get to this point
    git_ref = "main"

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
_eups_epilog = f"""

.. |eups-tag| replace:: {eups_tag}
.. |eups-tag-mono| replace:: ``{eups_tag}``
.. |eups-tag-bold| replace:: **{eups_tag}**
"""
rst_epilog = f"{rst_epilog}\n\n{_eups_epilog}"  # noqa: F405
