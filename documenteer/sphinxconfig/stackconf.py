# Some configurations based on astropy-helpers
# https://github.com/astropy/astropy-helpers/blob/master/astropy_helpers/sphinx/conf.py
# see licenses/astropy-helpers.txt
"""Sphinx configuration defaults for LSST Stack packages."""

import datetime
import sys
import warnings

import lsst_sphinx_bootstrap_theme

from .utils import read_git_commit_timestamp


def build_package_configs(project_name,
                          version='unknown',
                          copyright=None,
                          doxygen_xml_dirname=None):
    """Builds a `dict` of Sphinx configurations useful for the ``doc/conf.py``
    files of individual LSST Stack packages.

    The ``doc/conf.py`` of packages can ingest these configurations via

    .. code:: python

       from documenteer.sphinxconfing.stackconf import build_package_configs

       _g = globals()
       _g.update(build_package_configs(
           project_name='afw',
           version=lsst.afw.version.__version__))

    You can subsequently customize the Sphinx configuration by directly
    assigning global variables, as usual in a Sphinx ``config.py``, e.g.:

    .. code:: python

       copyright = '2016 Association of Universities for '
                   'Research in Astronomy, Inc.'

    Parameters
    ----------
    project_name : str
        Name of the package.
    copyright : str, optional
        Copyright statement. Do not include the 'Copyright (c)' string; it'll
        be added automatically.
    version : str
        Version string. Use the ``__version__`` member in a package's
        ``version`` module.
    doxygen_xml_dirname : str
        Path to doxygen-generated XML, allowing C++ APIs to be documented
        through breathe. If not set, the breathe sphinx extension will not be
        enabled.

    Returns
    -------
    c : dict
        Dictionary of configurations that should be added to the ``conf.py``
        global namespace via::

            _g = global()
            _g.update(c)
    """
    try:
        date = read_git_commit_timestamp()
    except Exception:
        date = datetime.datetime.now()

    c = {}
    c['project'] = project_name
    if copyright is not None:
        c['copyright'] = copyright
    else:
        c['copyright'] = 'Copyright {:s} LSST contributors.'.format(
            date.strftime('%Y-%m-%d'))
    c['version'] = version
    c['release'] = version

    c['today'] = date.strftime('%Y-%m-%d')

    # Sphinx extension modules
    c['extensions'] = [
        'sphinx.ext.autodoc',
        'sphinx.ext.doctest',
        'sphinx.ext.intersphinx',
        'sphinx.ext.todo',
        'sphinx.ext.coverage',
        'sphinx.ext.mathjax',
        'sphinx.ext.ifconfig',
        'sphinx.ext.viewcode',
        'sphinx-prompt',
        'astropy_helpers.extern.numpydoc.numpydoc',
        'astropy_helpers.extern.automodapi.autodoc_enhancements',
        'astropy_helpers.extern.automodapi.automodsumm',
        'astropy_helpers.extern.automodapi.automodapi',
        'astropy_helpers.sphinx.ext.tocdepthfix',
        'astropy_helpers.sphinx.ext.doctest',
        'astropy_helpers.sphinx.ext.changelog_links',
        'astropy_helpers.extern.automodapi.smart_resolver',
        'documenteer.sphinxext',
    ]

    # The suffix(es) of source filenames.
    # You can specify multiple suffix as a list of string:
    c['source_suffix'] = '.rst'

    # The encoding of source files.
    c['source_encoding'] = 'utf-8-sig'

    # The master toctree document.
    c['master_doc'] = 'index'

    # List of patterns, relative to source directory, that match files and
    # directories to ignore when looking for source files.
    c['exclude_patterns'] = ['_build', 'README.rst']

    # If true, `todo` and `todoList` produce output, else they produce nothing.
    c['todo_include_todos'] = True

    # Configuration for Intersphinx
    c['intersphinx_mapping'] = {
        'python': ('http://docs.python.org/3/', None),
        # FIXME add local object cache
        # 'pythonloc': ('http://docs.python.org/',
        #               os.path.abspath(
        #                   os.path.join(os.path.dirname(__file__),
        #                                'local/python3_local_links.inv'))),
        'numpy': ('http://docs.scipy.org/doc/numpy/', None),
        'scipy': ('http://docs.scipy.org/doc/scipy/reference/', None),
        'matplotlib': ('http://matplotlib.org/', None),
        'astropy': ('http://docs.astropy.org/en/stable/', None),
        'h5py': ('http://docs.h5py.org/en/latest/', None)
    }

    # Revert python intersphinx to Py 2 if that's the build environment
    if sys.version_info[0] == 2:
        c['intersphinx_mapping']['python'] = ('http://docs.python.org/2/',
                                              None)
        # FIXME add local object cache
        # c['intersphinx_mapping']['pythonloc'] = (
        #     'http://docs.python.org/',
        #     os.path.abspath(os.path.join(os.path.dirname(__file__),
        #                     'local/python2_local_links.inv')))

    # The reST default role (used for this markup: `text`)
    c['default_role'] = 'obj'

    # This is added to the end of RST files - a good place to put substitutions
    # to be used globally.
    c['rst_epilog'] = """
.. _Astropy: http://astropy.org
    """

    # A list of warning types to suppress arbitrary warning messages. We mean
    # to override directives in
    # astropy_helpers.sphinx.ext.autodoc_enhancements, thus need to ignore
    # those warning. This can be removed once the patch gets released in
    # upstream Sphinx (https://github.com/sphinx-doc/sphinx/pull/1843).
    # Suppress the warnings requires Sphinx v1.4.2
    c['suppress_warnings'] = ['app.add_directive', ]

    try:
        import matplotlib.sphinxext.plot_directive
        c['extensions'] += [matplotlib.sphinxext.plot_directive.__name__]
    except (ImportError, AttributeError):
        # AttributeError is checked here in case matplotlib is installed but
        # Sphinx isn't.  Note that this module is imported by the config file
        # generator, even if we're not building the docs.
        warnings.warn(
            "matplotlib's plot_directive could not be imported. " +
            "Inline plots will not be included in the output")

    # Don't show summaries of the members in each class along with the
    # class' docstring
    c['numpydoc_show_class_members'] = False

    c['autosummary_generate'] = True

    c['automodapi_toctreedirnm'] = 'py-api'

    # Class documentation should contain *both* the class docstring and
    # the __init__ docstring
    c['autoclass_content'] = "both"

    # Render inheritance diagrams in SVG
    c['graphviz_output_format'] = "svg"

    c['graphviz_dot_args'] = [
        '-Nfontsize=10',
        '-Nfontname=Helvetica Neue, Helvetica, Arial, sans-serif',
        '-Efontsize=10',
        '-Efontname=Helvetica Neue, Helvetica, Arial, sans-serif',
        '-Gfontsize=10',
        '-Gfontname=Helvetica Neue, Helvetica, Arial, sans-serif'
    ]

    if doxygen_xml_dirname is not None:
        c['extensions'].append('breathe')
        c['breathe_projects'] = {project_name: doxygen_xml_dirname}
        c['breathe_default_project'] = project_name

    # -- Options for HTML output ----------------------------------------------

    c['templates_path'] = [
        '_templates',
        lsst_sphinx_bootstrap_theme.get_html_templates_path()]

    c['html_theme'] = 'lsst_sphinx_bootstrap_theme'
    c['html_theme_path'] = [lsst_sphinx_bootstrap_theme.get_html_theme_path()]

    c['numfig'] = True
    c['numfig_format'] = {'figure': 'Figure %s',
                          'table': 'Table %s',
                          'code-block': 'Listing %s'}

    # Theme options are theme-specific and customize the look and feel of a
    # theme further.  For a list of options available for each theme, see the
    # documentation.
    c['html_theme_options'] = {}

    # The name for this set of Sphinx documents.  If None, it defaults to
    # "<project> v<release> documentation".
    c['html_title'] = c['project']

    # A shorter title for the navigation bar.  Default is the same as
    # html_title.
    c['html_short_title'] = c['project']

    # The name of an image file (relative to this directory) to place at the
    # top of the sidebar.
    c['html_logo'] = None

    # The name of an image file (within the static path) to use as favicon of
    # the docs.  This file should be a Windows icon file (.ico) being 16x16 or
    # 32x32 pixels large.
    c['html_favicon'] = None

    # Add any paths that contain custom static files (such as style sheets)
    # here, relative to this directory. They are copied after the builtin
    # static files, so a file named "default.css" will overwrite the builtin
    # "default.css".
    c['html_static_path'] = ['_static']

    # Add any extra paths that contain custom files (such as robots.txt or
    # .htaccess) here, relative to this directory. These files are copied
    # directly to the root of the documentation.
    # html_extra_path = []

    # If not '', a 'Last updated on:' timestamp is inserted at every page
    # bottom, using the given strftime format.
    c['html_last_updated_fmt'] = '%b %d, %Y'

    # If true, SmartyPants will be used to convert quotes and dashes to
    # typographically correct entities.
    c['html_use_smartypants'] = True

    # If false, no module index is generated.
    c['html_domain_indices'] = False

    # If false, no index is generated.
    c['html_use_index'] = False

    # If true, the index is split into individual pages for each letter.
    c['html_split_index'] = False

    # If true, links to the reST sources are added to the pages.
    c['html_show_sourcelink'] = True

    # If true, "Created using Sphinx" is shown in the HTML footer. Default is
    # True.
    c['html_show_sphinx'] = True

    # If true, "(C) Copyright ..." is shown in the HTML footer. Default is
    # True.
    c['html_show_copyright'] = True

    # If true, an OpenSearch description file will be output, and all pages
    # will contain a <link> tag referring to it.  The value of this option must
    # be the base URL from which the finished HTML is served.
    # html_use_opensearch = ''

    # This is the file name suffix for HTML files (e.g. ".xhtml").
    c['html_file_suffix'] = '.html'

    # Language to be used for generating the HTML full-text search index.
    c['html_search_language'] = 'en'

    # A dictionary with options for the search language support, empty by
    # default.  Now only 'ja' uses this config value
    # html_search_options = {'type': 'default'}

    # The name of a javascript file (relative to the configuration directory)
    # that implements a search results scorer. If empty, the default will be
    # used.
    # html_search_scorer = 'scorer.js'

    return c
