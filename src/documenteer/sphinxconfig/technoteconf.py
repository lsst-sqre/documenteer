"""Sphinx configuration bootstrapping for LSST Technical Notes.
"""

__all__ = ("configure_technote",)

import datetime
import glob
import os

import lsst_dd_rtd_theme
import yaml

from ..sphinxconfig.utils import (
    get_project_content_commit_date,
    read_git_branch,
)


def configure_technote(meta_stream):
    """Builds a ``dict`` of Sphinx configuration variables given a central
    configuration for LSST Design Documents and a metadata YAML file.

    This function refactors the common Sphinx ``conf.py`` script so that basic
    configurations are managed centrally in this module, while author-updatable
    metadata is stored in a ``metadata.yaml`` file in the document's
    repository.  To use this function, a ``conf.py`` need only look like

    .. code-block:: text

       import os
       from documenteer.sphinxconfig.technoteconf import configure_technote

       metadata_path = os.path.join(os.path.dirname(__file__), 'metadata.yaml')
       with open(metadata_path, 'r') as f:
           confs = configure_technote(f)
       g = global()
       g.update(confs)

    And ``metadata.yaml`` looks like:

    .. code-block:: yaml

       doc_id: 'LDM-152'
       doc_title: 'Data Management Middleware Design'
       copyright: '2015, AURA/LSST'
       authors:
           - 'Kian-Tat Lim'
           - 'Ray Plante'
           - 'Gregory Dubois-Felsmann'
       # Current document version
       last_revised: 'October 10, 2013'
       version: '10.0'
       # dev_version_suffix: None  # e.g. 'alpha'/'beta'/'rc' if necessary

    Parameters
    ----------
    meta_stream : `io.StringIO`
        A file stream (e.g., from :func:`open`) for the ``metadata.yaml``
        document in a design document's repository.

    Returns
    -------
    confs : `dict`
        Dictionary of configurations that should be added to the ``conf.py``
        global namespace.
    """
    _metadata = yaml.safe_load(meta_stream)
    confs = _build_confs(_metadata)
    return confs


def _build_confs(metadata):
    c = {}

    c["project"] = "{0}: {1}".format(metadata["doc_id"], metadata["doc_title"])

    c["author"] = ", ".join(metadata["authors"])  # FIXME add oxford comma

    c["copyright"] = metadata["copyright"]

    # List of patterns, relative to source directory, that match files and
    # directories to ignore when looking for source files.
    c["exclude_patterns"] = metadata.get(
        "exclude_patterns", ["_build", "README.rst"]
    )

    # attempt to obtain the version as the Git branch
    try:
        c["version"] = read_git_branch()
        c["git_branch"] = c["version"]
    except Exception as e:
        print("Caught exception: {}".format(e))
        print("Cannot get git branch information.")
        # defaults
        c["version"] = "Unknown"
        c["git_branch"] = "master"

    # Override with YAML metadata
    if "version" in metadata:
        c["version"] = metadata["version"]

    if "github_url" in metadata:
        c["github_url"] = metadata["github_url"]
        if not c["github_url"].endswith("/"):
            c["github_url"] = c["github_url"] + "/"
        c["edit_url"] = "{base}blob/{branch}/index.rst".format(
            base=c["github_url"], branch=c["git_branch"]
        )
    else:
        c["github_url"] = None
        c["edit_url"] = None

    # The full version, including alpha/beta/rc tags.
    if "dev_version_suffix" in metadata:
        c["release"] = "".join((c["version"], metadata["dev_version_suffix"]))
    else:
        c["release"] = c["version"]

    # Add a version suffix, if available
    if "dev_version_suffix" in metadata:
        c["release"] = "".join((c["release"], metadata["dev_version_suffix"]))

    if "last_revised" in metadata:
        date = datetime.datetime.strptime(metadata["last_revised"], "%Y-%m-%d")
    else:
        # obain date from git commit at most recent content commit since HEAD
        try:
            date = get_project_content_commit_date(
                exclusions=c["exclude_patterns"]
            )
        except Exception as e:
            print("Caught exception: {}".format(e))
            print("Cannot get project content git commit date.")
            date = datetime.datetime.now()
    c["today"] = date.strftime("%Y-%m-%d")

    # This is available to Jinja2 templates
    c["html_context"] = {
        "author_list": metadata["authors"],
        "doc_id": metadata["doc_id"],
        "doc_title": metadata["doc_title"],
        "last_revised": c["today"],
        "git_branch": c["git_branch"],
        "github_url": c["github_url"],
        "edit_url": c["edit_url"],
    }

    # -- General Sphinx configurations ---------------------------------------

    # Sphinx extension modules
    c["extensions"] = [
        "sphinx.ext.intersphinx",
        "sphinx.ext.todo",
        "sphinx.ext.mathjax",
        "sphinx.ext.ifconfig",
        "sphinx-prompt",
        "sphinxcontrib.bibtex",
        "documenteer.sphinxext",
        "documenteer.sphinxext.bibtex",
    ]

    # The suffix(es) of source filenames.
    # You can specify multiple suffix as a list of string:
    c["source_suffix"] = ".rst"

    # The encoding of source files.
    c["source_encoding"] = "utf-8-sig"

    # The master toctree document.
    c["master_doc"] = "index"

    # If true, `todo` and `todoList` produce output, else they produce nothing.
    c["todo_include_todos"] = True

    # Configuration for Intersphinx
    c["intersphinx_mapping"] = {}
    # Add Python 3 intersphinx inventory in projects via
    # c['intersphinx_mapping']['python'] = ('https://docs.python.org/3', None)

    # -- sphinxcontrib-bibtex ------------------------------------------------
    # -- See https://sphinxcontrib-bibtex.readthedocs.io/

    c["bibtex_bibfiles"] = []
    if os.path.exists("local.bib"):
        c["bibtex_bibfiles"].append("local.bib")
    for path in glob.glob("lsstbib/*.bib"):
        c["bibtex_bibfiles"].append(path)

    c["bibtex_default_style"] = "lsst_aa"

    # -- Options for HTML output ----------------------------------------------

    # see https://github.com/snide/sphinx_rtd_theme
    #     #using-this-theme-locally-then-building-on-read-the-docs
    # for how to change themes on RTD vs local
    # on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
    c["templates_path"] = ["_templates"]
    c["html_theme"] = "lsst_dd_rtd_theme"
    c["html_theme_path"] = [lsst_dd_rtd_theme.get_html_theme_path()]

    c["numfig"] = True
    c["numfig_format"] = {
        "figure": "Figure %s",
        "table": "Table %s",
        "code-block": "Listing %s",
    }

    # Theme options are theme-specific and customize the look and feel of a
    # theme further.  For a list of options available for each theme, see the
    # documentation.
    c["html_theme_options"] = {}

    # The name for this set of Sphinx documents.  If None, it defaults to
    # "<project> v<release> documentation".
    c["html_title"] = c["project"]

    # A shorter title for the navigation bar.  Default is the same as
    # html_title.
    c["html_short_title"] = metadata["doc_id"]

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
    c["html_domain_indices"] = False

    # If false, no index is generated.
    c["html_use_index"] = False

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

    # MathJax CDN
    c["mathjax_path"] = (
        "https://cdn.mathjax.org/mathjax/latest/" + "MathJax.js?config=default"
    )

    # A dictionary with options for the search language support, empty by
    # default.  Now only 'ja' uses this config value
    # html_search_options = {'type': 'default'}

    # The name of a javascript file (relative to the configuration directory)
    # that implements a search results scorer. If empty, the default will be
    # used.
    # html_search_scorer = 'scorer.js'

    # Output file base name for HTML help builder.
    c["htmlhelp_basename"] = "{0}_{1}".format(
        metadata["doc_id"], metadata["doc_title"].replace(" ", "_")
    )

    # -- Options for LaTeX output ---------------------------------------------

    c["latex_elements"] = {
        # The paper size ('letterpaper' or 'a4paper').
        # 'papersize': 'letterpaper',
        # The font size ('10pt', '11pt' or '12pt').
        # 'pointsize': '10pt',
        # Additional stuff for the LaTeX preamble.
        # 'preamble': '',
        # Latex figure (float) alignment
        # 'figure_align': 'htbp',
    }

    # Grouping the document tree into LaTeX files. List of tuples
    # (source start file, target name, title,
    #  author, documentclass [howto, manual, or own class]).
    c["latex_documents"] = [
        (
            c["master_doc"],
            "{0}_{1}.tex".format(
                metadata["doc_id"], metadata["doc_title"].replace(" ", "_")
            ),
            c["project"],
            c["author"],
            "manual",
        ),
    ]

    # The name of an image file (relative to this directory) to place at the
    # top of the title page.
    # latex_logo = None

    # For "manual" documents, if this is true, then toplevel headings are
    # parts, not chapters.
    # latex_use_parts = False

    # If true, show page references after internal links.
    # latex_show_pagerefs = False

    # If true, show URL addresses after external links.
    # latex_show_urls = False

    # Documents to append as an appendix to all manuals.
    # latex_appendices = []

    # If false, no module index is generated.
    # latex_domain_indices = True

    # -- Options for Epub output ----------------------------------------------

    # Bibliographic Dublin Core info.
    c["epub_title"] = c["project"]
    c["epub_author"] = c["author"]
    c["epub_publisher"] = "AURA/LSST"
    c["epub_copyright"] = c["copyright"]

    # The basename for the epub file. It defaults to the project name.
    c["epub_basename"] = c["project"].replace(" ", "_")

    # The HTML theme for the epub output. Since the default themes are not
    # optimized for small screen space, using the same theme for HTML and epub
    # output is usually not wise. This defaults to 'epub', a theme designed to
    # save visual space.
    c["epub_theme"] = "epub"

    # The language of the text. It defaults to the language option
    # or 'en' if the language is not set.
    c["epub_language"] = "en"

    # A list of files that should not be packed into the epub file.
    c["epub_exclude_files"] = ["search.html"]

    # If false, no index is generated.
    c["epub_use_index"] = False

    return c
