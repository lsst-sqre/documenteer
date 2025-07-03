"""Sphinx configuration for Rubin Observatory User Guides.

To use this configuration in a Sphinx technote project, write a conf.py
containing::

    from documenteer.conf.guide import *
"""

import warnings
from typing import Any

from sphinx.deprecation import RemovedInNextVersionWarning

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
# #GRAPHVIZ
#     Graphviz configuration
# #MYST
#     MyST markdown configurations
# #MERMIAID
#     Mermaid diagram support
# #OPENGRAPH
#     OpenGraph metadata support
# #OPENAPI
#     OpenAPI/redoc support
# #REDIRECTS
#     Sphinx-rediraffe support


# Ordered as they are declared in this module
__all__ = [
    # EXT
    "extensions",
    # SPHINX
    "project",
    "author",
    "copyright",
    "version",
    "release",
    "source_suffix",
    "root_doc",
    "language",
    "exclude_patterns",
    "default_role",
    "nitpicky",
    "nitpick_ignore",
    "nitpick_ignore_regex",
    "templates_path",
    "rst_epilog",
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
    "html_context",
    "html_theme_options",
    "html_sidebars",
    "html_title",
    "html_short_title",
    "html_baseurl",
    "html_static_path",
    "html_css_files",
    "html_show_sourcelink",
    "favicons",
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
    "myst_fence_as_directive",
    # MERMAID
    "mermaid_output_format",
    # OPENGRAPH
    "ogp_site_url",
    "ogp_site_name",
    "ogp_use_first_image",
    # OPENAPI
    "documenteer_openapi_generator",
    "documenteer_openapi_path",
    "redoc",
    "redoc_version",
    # Sphinx jinja
    "jinja_contexts",
    # Sphinx rediraffe
    "rediraffe_redirects",
]

# Suppress warnings about deprecated features in future Sphinx versions.
# This is noise for users because Documenteer itself constrains the Sphinx
# version.
warnings.filterwarnings(
    "ignore",
    category=RemovedInNextVersionWarning,
)

_conf = DocumenteerConfig.find_and_load()


# ============================================================================
# #EXT Sphinx extensions
# ============================================================================

extensions = [
    "sphinxcontrib.jquery",
    "myst_nb",  # enables myst-parser as well
    "sphinx_copybutton",
    "sphinx_design",
    "sphinxcontrib.mermaid",
    "sphinxext.opengraph",
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.ifconfig",
    "sphinx_prompt",
    "sphinx_jinja",
    "sphinxcontrib.youtube",
    "sphinxext.rediraffe",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
    "sphinx_automodapi.automodapi",
    "sphinx_automodapi.smart_resolver",
    "sphinx_favicon",
    "documenteer.ext.jira",
    "documenteer.ext.lsstdocushare",
    "documenteer.ext.mockcoderefs",
    "documenteer.ext.remotecodeblock",
    "documenteer.ext.openapi",
    "documenteer.ext.redoc",
]
_conf.append_extensions(extensions)

# ============================================================================
# #SPHINX Core Sphinx configurations
# ============================================================================

project = _conf.project

author = "Rubin Observatory"

copyright = _conf.copyright  # noqa: A001

version = _conf.version
release = version

# The source file suffixes for .md and .ipynb are automatically managed by
# myst-nb.
source_suffix = {
    ".rst": "restructuredtext",
}

root_doc = "index"

language = "en"

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = [
    "_build",
    "README.rst",
    "README.md",
    ".venv",
    "venv",
    "requirements.txt",
    ".github",
    ".tox",
]
_conf.extend_exclude_patterns(exclude_patterns)

if _conf.rst_epilog_path:
    exclude_patterns.append(str(_conf.rst_epilog_path))

# The reST default role cross-links Python (used for this markup: `text`)
default_role = "py:obj"

# Escalate warnings ot errors if True
nitpicky = _conf.nitpicky

# Warnings to ignore
nitpick_ignore: list[tuple[str, str]] = [
    # Ignore missing cross-references for modules that don't provide
    # intersphinx.  The documentation itself should use double-quotes instead
    # of single-quotes to not generate a reference, but automatic references
    # are generated from the type signatures and can't be avoided.
    ("py:class", "fastapi.applications.FastAPI"),
    ("py:class", "fastapi.datastructures.DefaultPlaceholder"),
    ("py:class", "fastapi.exceptions.HTTPException"),
    ("py:class", "fastapi.params.Depends"),
    ("py:class", "fastapi.routing.APIRoute"),
    ("py:class", "httpx.AsyncClient"),
    ("py:exc", "fastapi.HTTPException"),
    ("py:exc", "fastapi.exceptions.RequestValidationError"),
    ("py:exc", "httpx.HTTPError"),
    ("py:obj", "ConfigDict"),
    ("py:obj", "fastapi.routing.APIRoute"),
    ("py:class", "kubernetes_asyncio.client.api_client.ApiClient"),
    ("py:class", "pydantic.main.BaseModel"),
    ("py:class", "pydantic.networks.AnyHttpUrl"),
    ("py:class", "pydantic.networks.IPvAnyNetwork"),
    ("py:class", "pydantic.types.SecretStr"),
    ("py:class", "pydantic.utils.Representation"),
    ("py:class", "pydantic_core._pydantic_core.Url"),
    ("py:class", "pydantic_core._pydantic_core.ValidationError"),
    ("py:class", "pydantic_settings.main.BaseSettings"),
    ("py:class", "pydantic_settings.sources.CliSettingsSource"),
    ("py:obj", "safir.pydantic.validate_exactly_one_of.<locals>.validator"),
    ("py:class", "starlette.datastructures.URL"),
    ("py:class", "starlette.middleware.base.BaseHTTPMiddleware"),
    ("py:class", "starlette.requests.Request"),
    ("py:class", "starlette.responses.Response"),
    ("py:class", "starlette.routing.Route"),
    ("py:class", "starlette.routing.BaseRoute"),
    ("py:exc", "starlette.exceptions.HTTPException"),
    # asyncio.Lock is documented, and that's what all the code references, but
    # the combination of Sphinx extensions we're using confuse themselves and
    # there doesn't seem to be any way to fix this.
    ("py:class", "asyncio.locks.Lock"),
]
_conf.append_nitpick_ignore(nitpick_ignore)

nitpick_ignore_regex: list[tuple[str, str]] = [
    ("py:class", r"kubernetes_asyncio\.client\.models\..*"),
    # Bug in autodoc_pydantic.
    ("py:obj", r".*\.all fields"),
]
_conf.append_nitpick_ignore_regex(nitpick_ignore_regex)

# A list of paths that contain extra templates (or templates that overwrite
# builtin/theme-specific templates).
templates_path = [get_template_dir("pydata")]

# Common reStructuredText substitutions and links
rst_epilog = _conf.rst_epilog

# ============================================================================
# #INTER Intersphinx configuration
# ============================================================================

intersphinx_mapping: dict[str, tuple[str, str | None]] = {}
_conf.extend_intersphinx_mapping(intersphinx_mapping)

intersphinx_timeout = 10.0  # seconds

intersphinx_cache_limit = 5  # days


# ============================================================================
# #LINKCHECK Linkcheck builder configuration
# ============================================================================

linkcheck_retries = 2

linkcheck_ignore = [
    # Tucson IT infrastructure sometimes goes down or has TLS issues
    r"^https://ls.st/",
]
_conf.append_linkcheck_ignore(linkcheck_ignore)

linkcheck_timeout = 15

# ============================================================================
# #HTML HTML builder and theme configuration
# ============================================================================

html_theme = "pydata_sphinx_theme"

# Context available to Jinja templates
html_context: dict[str, Any] = {}

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
    "header_links_before_dropdown": _conf.header_links_before_dropdown,
    "external_links": [{"name": "Rubin docs", "url": "https://www.lsst.io"}],
    "icon_links": [],
    "logo": {
        "image_light": "rubin-titlebar-imagotype-light.svg",
        "image_dark": "rubin-titlebar-imagotype-dark.svg",
        "text": project,
    },
    "pygments_light_style": "xcode",
    "pygments_dark_style": "github-dark",
}

if _conf.github_url:
    if not isinstance(html_theme_options["icon_links"], list):
        raise TypeError("icon_links must be a list")
    html_theme_options["icon_links"].append(
        {
            "name": "GitHub",
            "url": _conf.github_url,
            "icon": "fab fa-github-square",
            "type": "fontawesome",
        }
    )

favicons = [
    {
        "href": "rubin-favicon-transparent-32px.png",
        "rel": "icon",
        "sizes": "32x32",
        "type": "image/png",
    },
    {
        "href": "rubin-favicon.svg",
        "rel": "icon",
        "type": "image/svg+xml",
    },
]


# Configure the "Edit this page" link
_conf.set_edit_on_github(html_theme_options, html_context)

# Specifies templates to put in the primary (left) sidebars of
# specific pages (by their docname or pattern). An empty list results in the
# sidebar being dropped altogether.
html_sidebars: dict[str, list[str]] = {"index": [], "changelog": []}
_conf.disable_primary_sidebars(html_sidebars)

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = project

# A shorter title for the navigation bar.  Default is the same as html_title.
html_short_title = project

# The base URL of the root of the HTML documentation. This is used to set
# the canonical URL link relation
html_baseurl = _conf.base_url

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path: list[str] = [
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
automodapi_toctreedirnm = _conf.automodapi_toctreedirm

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
napoleon_type_aliases: dict[str, str] | None = None
napoleon_attr_annotations = True

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
# #MYST MyST markdown configurations
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

# ============================================================================
# #MERMIAID Mermaid diagram support
# https://github.com/mgaitan/sphinxcontrib-mermaid
# https://mermaid-js.github.io/mermaid/#/
# ============================================================================

# The raw format renders the diagram client-side, and doesn't require a
# Mermaid CLI installation
mermaid_output_format = "raw"

# Code fences that can be interpreted as directives
myst_fence_as_directive = ["mermaid"]

# ============================================================================
# #OPENGRAPH OpenGraph diagram support
# https://github.com/wpilibsuite/sphinxext-opengraph
# https://ogp.me/
# ============================================================================

ogp_site_url = _conf.base_url
ogp_site_name = _conf.project
ogp_use_first_image = True

# ============================================================================
# #OPEN OpenAPI/Redoc support
# documenteer.ext.openapi
# documenteer.ext.redoc
# ============================================================================

redoc_version = "v2.5.0"

if _conf.conf.project.openapi is not None:
    if _conf.conf.project.openapi.generator is not None:
        documenteer_openapi_generator: dict[str, Any] | None = {
            "func": _conf.conf.project.openapi.generator.function,
            "args": _conf.conf.project.openapi.generator.positional_args,
            "kwargs": _conf.conf.project.openapi.generator.keyword_args,
        }
    else:
        documenteer_openapi_generator = None
    documenteer_openapi_path: str | None = (
        _conf.conf.project.openapi.openapi_path
    )
    html_static_path.append(_conf.conf.project.openapi.openapi_path)
    redoc: list[Any] | None = [
        {
            "name": "REST API",
            "page": _conf.conf.project.openapi.doc_path,
            "spec_path": _conf.conf.project.openapi.openapi_path,
            "opts": {
                "hide-hostname": True,
                "path-in-middle-panel": True,
            },
        }
    ]
else:
    documenteer_openapi_generator = None
    documenteer_openapi_path = None
    redoc = []

# ============================================================================
# #JINJA Sphinx Jinja support
# ============================================================================
jinja_contexts: dict[str, Any] = {}

# ============================================================================
# #REDIRECTS Sphinx-rediraffe support
# https://sphinxext-rediraffe.readthedocs.io/en/latest/
# ============================================================================
rediraffe_redirects: dict[str, str] = _conf.redirects
