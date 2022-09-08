"""Sphinx configuration defaults for LSST Stack packages.

Notes
-----
Some configurations based on astropy-helpers
https://github.com/astropy/astropy-helpers/blob/master/astropy_helpers/sphinx/conf.py
see licenses/astropy-helpers.txt
"""

__all__ = ("build_package_configs", "build_pipelines_lsst_io_configs")

import datetime
import os
import sys

import lsst_sphinx_bootstrap_theme

from documenteer.packagemetadata import Semver, get_package_version_semver

from .utils import read_git_commit_timestamp


def _insert_extensions(c):
    """Insert the ``extensions`` variable into the configuration state."""
    # The extension name for sphinx-jinja changed with version 2.0.0
    _sphinx_jinja_ext_name = "sphinx_jinja"
    try:
        if get_package_version_semver("sphinx-jinja") < Semver.parse("2.0.0"):
            # Use older sphinx jinja name for sphinx-jinja < 2.0.0
            _sphinx_jinja_ext_name = "sphinxcontrib.jinja"
    except Exception as e:
        print(f"Error getting sphinx-jinja version: {str(e)}")

    c["extensions"] = [
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
        "numpydoc",
        "sphinx_automodapi.automodapi",
        "sphinx_automodapi.smart_resolver",
        "documenteer.sphinxext",
        "documenteer.sphinxext.lssttasks",
    ]
    return c


def _insert_intersphinx_mapping(c):
    """Insert the ``intersphinx_mapping``, ``intersphinx_timeout`` and
    ``intersphinx_cache_limit`` variableis into the configuration state.
    """
    c["intersphinx_mapping"] = {
        "python": ("https://docs.python.org/3/", None),
        # FIXME add local object cache
        # 'pythonloc': ('http://docs.python.org/',
        #               os.path.abspath(
        #                   os.path.join(os.path.dirname(__file__),
        #                                'local/python3_local_links.inv'))),
        "numpy": ("https://docs.scipy.org/doc/numpy/", None),
        "scipy": ("https://docs.scipy.org/doc/scipy/reference/", None),
        "matplotlib": ("https://matplotlib.org/", None),
        "sklearn": ("https://scikit-learn.org/stable/", None),
        "pandas": ("https://pandas.pydata.org/pandas-docs/stable/", None),
        "astropy": ("http://docs.astropy.org/en/v3.0.x/", None),
        "astro_metadata_translator": (
            "https://astro-metadata-translator.lsst.io",
            None,
        ),
        "firefly_client": ("https://firefly-client.lsst.io", None),
    }
    c["intersphinx_timeout"] = 10.0  # seconds
    c["intersphinx_cache_limit"] = 5  # days
    return c


def _insert_html_configs(c, *, project_name, short_project_name):
    """Insert HTML theme configurations."""
    # Use the lsst-sphinx-bootstrap-theme
    c["templates_path"] = [
        "_templates",
        lsst_sphinx_bootstrap_theme.get_html_templates_path(),
    ]
    c["html_theme"] = "lsst_sphinx_bootstrap_theme"
    c["html_theme_path"] = [lsst_sphinx_bootstrap_theme.get_html_theme_path()]

    # Theme options are theme-specific and customize the look and feel of a
    # theme further.  For a list of options available for each theme, see the
    # documentation.
    c["html_theme_options"] = {"logotext": short_project_name}

    # The name for this set of Sphinx documents.  If None, it defaults to
    # "<project> v<release> documentation".
    c["html_title"] = project_name

    # A shorter title for the navigation bar.  Default is the same as
    # html_title.
    c["html_short_title"] = short_project_name

    # The name of an image file (relative to this directory) to place at the
    # top of the sidebar.
    c["html_logo"] = None

    # The name of an image file (within the static path) to use as favicon of
    # the docs.  This file should be a Windows icon file (.ico) being 16x16 or
    # 32x32 pixels large.
    c["html_favicon"] = None

    # Add any paths that contain custom static files (such as style sheets)
    # here, relative to this directory. They are copied after the builtin
    # static files, so a file named "default.css" will overwrite the builtin
    # "default.css".
    if os.path.isdir("_static"):
        c["html_static_path"] = ["_static"]
    else:
        # If a project does not have a _static/ directory, don't list it
        # so that there isn't a warning.
        c["html_static_path"] = []

    # Add any extra paths that contain custom files (such as robots.txt or
    # .htaccess) here, relative to this directory. These files are copied
    # directly to the root of the documentation.
    # html_extra_path = []

    # If not '', a 'Last updated on:' timestamp is inserted at every page
    # bottom, using the given strftime format.
    c["html_last_updated_fmt"] = "%b %d, %Y"

    # If true, SmartyPants will be used to convert quotes and dashes to
    # typographically correct entities.
    c["html_use_smartypants"] = True

    # If false, no module index is generated.
    c["html_domain_indices"] = True

    # If false, no index is generated.
    c["html_use_index"] = True

    # If true, the index is split into individual pages for each letter.
    c["html_split_index"] = False

    # If true, links to the reST sources are added to the pages.
    c["html_show_sourcelink"] = True

    # If true, "Created using Sphinx" is shown in the HTML footer. Default is
    # True.
    c["html_show_sphinx"] = True

    # If true, "(C) Copyright ..." is shown in the HTML footer. Default is
    # True.
    c["html_show_copyright"] = True

    # If true, an OpenSearch description file will be output, and all pages
    # will contain a <link> tag referring to it.  The value of this option must
    # be the base URL from which the finished HTML is served.
    # html_use_opensearch = ''

    # This is the file name suffix for HTML files (e.g. ".xhtml").
    c["html_file_suffix"] = ".html"

    # Language to be used for generating the HTML full-text search index.
    c["html_search_language"] = "en"

    # A dictionary with options for the search language support, empty by
    # default.  Now only 'ja' uses this config value
    # html_search_options = {'type': 'default'}

    # The name of a javascript file (relative to the configuration directory)
    # that implements a search results scorer. If empty, the default will be
    # used.
    # html_search_scorer = 'scorer.js'

    return c


def _insert_common_sphinx_configs(c, *, project_name):
    """Add common core Sphinx configurations to the state."""
    c["project"] = project_name

    # The suffix(es) of source filenames.
    # You can specify multiple suffix as a list of string:
    c["source_suffix"] = ".rst"

    # The encoding of source files.
    c["source_encoding"] = "utf-8-sig"

    # The master toctree document.
    c["master_doc"] = "index"

    # Configure figure numbering
    c["numfig"] = True
    c["numfig_format"] = {
        "figure": "Figure %s",
        "table": "Table %s",
        "code-block": "Listing %s",
    }

    # The reST default role (used for this markup: `text`)
    c["default_role"] = "obj"

    # This is added to the end of RST files - a good place to put substitutions
    # to be used globally.
    c[
        "rst_epilog"
    ] = """
.. _Astropy: http://astropy.org
    """

    # A list of warning types to suppress arbitrary warning messages. We mean
    # to override directives in
    # astropy_helpers.sphinx.ext.autodoc_enhancements, thus need to ignore
    # those warning. This can be removed once the patch gets released in
    # upstream Sphinx (https://github.com/sphinx-doc/sphinx/pull/1843).
    # Suppress the warnings requires Sphinx v1.4.2
    c["suppress_warnings"] = [
        "app.add_directive",
    ]

    return c


def _insert_breathe_configs(c, *, project_name, doxygen_xml_dirname):
    """Add breathe extension configurations to the state."""
    if doxygen_xml_dirname is not None:
        c["breathe_projects"] = {project_name: doxygen_xml_dirname}
        c["breathe_default_project"] = project_name
    return c


def _insert_automodapi_configs(c):
    """Add configurations related to automodapi, autodoc, and numpydoc to the
    state.
    """
    # Don't show summaries of the members in each class along with the
    # class' docstring
    c["numpydoc_show_class_members"] = False

    c["autosummary_generate"] = True

    c["automodapi_toctreedirnm"] = "py-api"
    c["automodsumm_inherited_members"] = True

    # Docstrings for classes and methods are inherited from parents.
    c["autodoc_inherit_docstrings"] = True

    # Class documentation should only contain the class docstring and
    # ignore the __init__ docstring, account to LSST coding standards.
    # c['autoclass_content'] = "both"
    c["autoclass_content"] = "class"

    # Default flags for automodapi directives. Special members are dunder
    # methods.
    # NOTE: We want to used `inherited-members`, but it seems to be causing
    # documentation duplication in the automodapi listings. We're leaving
    # this out for now. See https://jira.lsstcorp.org/browse/DM-14782 for
    # additional notes.
    # NOTE: Without inherited members set, special-members doesn't need seem
    # to have an effect (even for special members where the docstrings are
    # directly written in the class, not inherited.
    # c['autodoc_default_flags'] = ['inherited-members']
    c["autodoc_default_flags"] = ["show-inheritance", "special-members"]

    return c


def _insert_graphviz_configs(c):
    """Insert configurations for graphviz to the state.

    Graphviz is primarily used by automodapi to create dependency
    diagrams for Python.
    """
    # Render inheritance diagrams in SVG
    c["graphviz_output_format"] = "svg"

    c["graphviz_dot_args"] = [
        "-Nfontsize=10",
        "-Nfontname=Helvetica Neue, Helvetica, Arial, sans-serif",
        "-Efontsize=10",
        "-Efontname=Helvetica Neue, Helvetica, Arial, sans-serif",
        "-Gfontsize=10",
        "-Gfontname=Helvetica Neue, Helvetica, Arial, sans-serif",
    ]

    return c


def _insert_single_package_eups_version(c, eups_version):
    """Insert version information into the configuration namespace.

    Parameters
    ----------
    eups_version
        The EUPS version string (as opposed to tag). This comes from the
        ``__version__`` attribute of individual modules and is only set for
        single package documentation builds that use the
        `build_package_configs` configuration entrypoint.

    Notes
    -----
    The variables are:

    ``release_eups_tag``
        Always ``current``.
    ``version``, ``release``
        Equal to ``eups_version``.
    ``release_git_ref``
        Always ``master``.
    ``scipipe_conda_ref``
        Always ``master``.
    ``newinstall_ref``
        Always ``master``.
    ``pipelines_demo_ref``
        Always ``master``.
    """
    c["release_eups_tag"] = "current"
    c["release_git_ref"] = "master"
    c["version"] = eups_version
    c["release"] = eups_version
    c["scipipe_conda_ref"] = "master"
    c["pipelines_demo_ref"] = "master"
    c["newinstall_ref"] = "master"
    return c


def _insert_eups_version(c):
    """Insert information about the current EUPS tag into the configuration
    namespace.

    The variables are:

    ``release_eups_tag``
        The EUPS tag (obtained from the ``EUPS_TAG`` environment variable,
        falling back to ``d_latest`` if not available).
    ``version``, ``release``
        Same as ``release_eups_tag``.
    ``release_git_ref``
        The git ref (branch or tag) corresponding ot the EUPS tag.
    ``scipipe_conda_ref``
        Git ref for the https://github.com/lsst/scipipe_conda_env repo.
    ``newinstall_ref``
        Git ref for the https://github.com/lsst/lsst repo.
    ``pipelines_demo_ref``
        Git ref for the https://github.com/lsst/lsst_dm_stack_demo repo.
    """
    # Attempt to get the eups tag from the build environment
    eups_tag = os.getenv("EUPS_TAG")
    if eups_tag is None:
        eups_tag = "d_latest"

    # Try to guess the git ref that corresponds to this tag
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

    # Now set variables for the Jinja context
    c["release_eups_tag"] = eups_tag
    c["release_git_ref"] = git_ref
    c["version"] = eups_tag
    c["release"] = eups_tag
    c["scipipe_conda_ref"] = git_ref
    c["pipelines_demo_ref"] = git_ref
    c["newinstall_ref"] = git_ref

    return c


def _insert_rst_epilog(c):
    """Insert the rst_epilog variable into the configuration.

    This should be applied after other configurations so that the epilog can
    use other configuration variables.
    """
    # Substitutions available on every page
    c[
        "rst_epilog"
    ] = """
.. |eups-tag| replace:: {eups_tag}
.. |eups-tag-mono| replace:: ``{eups_tag}``
.. |eups-tag-bold| replace:: **{eups_tag}**
    """.format(
        eups_tag=c["release_eups_tag"]
    )

    return c


def _insert_jinja_configuration(c):
    """Insert the configuration for the sphinx-jinja extension.

    The "default" Jinja context includes all variables in the conf.py
    configuration namespace.
    """
    c["jinja_contexts"] = {"default": c}

    return c


def build_package_configs(
    project_name, version=None, copyright=None, doxygen_xml_dirname=None
):
    """Builds a `dict` of Sphinx configurations useful for the ``doc/conf.py``
    files of individual LSST Stack packages.

    The ``doc/conf.py`` of packages can ingest these configurations via::

       from documenteer.sphinxconfig.stackconf import build_package_configs

       _g = globals()
       _g.update(build_package_configs(
           project_name='afw',
           version=lsst.afw.version.__version__))

    You can subsequently customize the Sphinx configuration by directly
    assigning global variables, as usual in a Sphinx ``config.py``, e.g.:

    .. code:: python

       copyright = "2016 Association of Universities for Research in Astronomy"

    Parameters
    ----------
    project_name : `str`
        Name of the package.
    copyright : `str`, optional
        Copyright statement. Do not include the 'Copyright (c)' string; it'll
        be added automatically.
    version : `str`
        Version string. Use the ``__version__`` member in a package's
        ``version`` module.
    doxygen_xml_dirname : `str`
        Path to doxygen-generated XML, allowing C++ APIs to be documented
        through breathe. If not set, the breathe sphinx extension will not be
        enabled.

    Returns
    -------
    c : `dict`
        Dictionary of configurations that should be added to the ``conf.py``
        global namespace via::

            _g = global()
            _g.update(c)
    """
    c = {}

    c = _insert_common_sphinx_configs(c, project_name=project_name)

    # HTML theme
    c = _insert_html_configs(
        c, project_name=project_name, short_project_name=project_name
    )

    # Sphinx extension modules
    c = _insert_extensions(c)

    # Intersphinx configuration
    c = _insert_intersphinx_mapping(c)

    # Breathe extension configuration
    c = _insert_breathe_configs(
        c, project_name=project_name, doxygen_xml_dirname=doxygen_xml_dirname
    )

    # Automodapi and numpydoc configurations
    c = _insert_automodapi_configs(c)

    # Graphviz configurations
    c = _insert_graphviz_configs(c)

    # Add versioning information
    c = _insert_single_package_eups_version(c, version)

    try:
        date = read_git_commit_timestamp()
    except Exception:
        date = datetime.datetime.now()

    if copyright is not None:
        c["copyright"] = copyright
    else:
        c["copyright"] = "{:s} LSST contributors".format(date.strftime("%Y"))

    c["today"] = date.strftime("%Y-%m-%d")

    # List of patterns, relative to source directory, that match files and
    # directories to ignore when looking for source files.
    c["exclude_patterns"] = [
        "_build",
        "README.rst",
    ]

    # Show rendered todo directives in package docs since they're developer
    # facing.
    c["todo_include_todos"] = True

    # Insert rst_epilog configuration
    c = _insert_rst_epilog(c)

    # Set up the context for the sphinx-jinja extension
    c = _insert_jinja_configuration(c)

    return c


def build_pipelines_lsst_io_configs(*, project_name, copyright=None):
    """Build a `dict` of Sphinx configurations that populate the ``conf.py``
    of the main pipelines_lsst_io Sphinx project for LSST Science Pipelines
    documentation.

    The ``conf.py`` file can ingest these configurations via::

       from documenteer.sphinxconfig.stackconf import \
           build_pipelines_lsst_io_configs

       _g = globals()
       _g.update(build_pipelines_lsst_io_configs(
           project_name='LSST Science Pipelines')

    You can subsequently customize the Sphinx configuration by directly
    assigning global variables, as usual in a Sphinx ``config.py``, e.g.::

       copyright = '2016 Association of Universities for '
                   'Research in Astronomy, Inc.'

    Parameters
    ----------
    project_name : `str`
        Name of the project
    copyright : `str`, optional
        Copyright statement. Do not include the 'Copyright (c)' string; it'll
        be added automatically.

    Returns
    -------
    c : dict
        Dictionary of configurations that should be added to the ``conf.py``
        global namespace via::

            _g = global()
            _g.update(c)
    """
    # Work around Sphinx bug related to large and highly-nested source files
    sys.setrecursionlimit(2000)

    c = {}

    c = _insert_common_sphinx_configs(c, project_name=project_name)

    # HTML theme
    c = _insert_html_configs(
        c, project_name=project_name, short_project_name=project_name
    )

    # Sphinx extension modules
    c = _insert_extensions(c)

    # Intersphinx configuration
    c = _insert_intersphinx_mapping(c)

    # Breathe extension configuration
    # FIXME configure this for multiple sites

    # Automodapi and numpydoc configurations
    c = _insert_automodapi_configs(c)

    # Graphviz configurations
    c = _insert_graphviz_configs(c)

    # Add versioning information
    c = _insert_eups_version(c)

    # Always use "now" as the date for the main site's docs because we can't
    # look at the Git history of each stack package.
    date = datetime.datetime.now()
    c["today"] = date.strftime("%Y-%m-%d")

    # Use this copyright for now. Ultimately we want to gather COPYRIGHT files
    # and build an integrated copyright that way.
    c["copyright"] = "2015-{year} LSST contributors".format(year=date.year)

    # Hide todo directives in the "published" documentation on the main site.
    c["todo_include_todos"] = False

    # List of patterns, relative to source directory, that match files and
    # directories to ignore when looking for source files.
    c["exclude_patterns"] = [
        "README.rst",
        # Build products
        "_build",
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
    ]

    # Insert rst_epilog configuration
    c = _insert_rst_epilog(c)

    # Set up the context for the sphinx-jinja extension
    c = _insert_jinja_configuration(c)

    return c
