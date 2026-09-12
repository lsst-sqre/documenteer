"""Sphinx configuration for Rubin technotes."""

import tomllib
import warnings
from contextlib import suppress
from pathlib import Path
from typing import NoReturn

from pydantic import ValidationError
from sphinx.deprecation import RemovedInNextVersionWarning
from sphinx.errors import ConfigError
from technote.sources.tomlsettings import TechnoteToml

from documenteer.conf import (
    extend_excludes_for_non_index_source,
    extend_static_paths_with_asset_extension,
    get_asset_path,
    get_template_dir,
)

from ._errors import fail_config
from ._technotecitation import TechnoteCitation
from ._tomlerrors import format_validation_error
from ._utils import (
    get_common_nitpick_ignore,
    get_common_nitpick_ignore_regex,
    get_technote_origin_base_url,
)


def _fail_technote_config(error: BaseException) -> NoReturn:
    """Report a technote.toml the technote package rejected, in the same
    words a documenteer.toml is rejected in, and end the process.

    The technote package validates technote.toml with pydantic and raises
    ``ConfigError("Syntax or validation issue in technote.toml")`` — a
    sentence that names no table, no field, and no value — keeping the
    `~pydantic.ValidationError` as the exception's cause. That cause is where
    everything an author needs is, so it is read back out and reported
    against technote's own model, which puts a malformed ``[technote] doi``
    or a lowercase code in ``[technote.lint] ignore`` in front of whoever
    wrote it instead of a pydantic frame.
    """
    cause = error.__cause__
    if isinstance(cause, ValidationError):
        message = format_validation_error(
            cause, root=TechnoteToml, source="technote.toml"
        )
    elif isinstance(error, tomllib.TOMLDecodeError):
        # technote parses the file before validating it, so a file TOML
        # itself cannot read escapes as the parser's own exception. Its
        # message carries the line and column, which is the whole of what
        # finds an unclosed quote or bracket.
        message = f"Syntax error in technote.toml: {error}"
    else:
        message = str(error)
    fail_config(message, source="technote.toml")


# Importing technote's preset is what reads and validates technote.toml, so
# it is also where a bad file stops the build. It is reported and exits here
# rather than being left to propagate: an exception raised while conf.py runs
# is rendered by Sphinx as a crash of Sphinx, which buries the message that
# says what to fix. See documenteer.conf._errors for why the exit has to be
# the one it is.
try:
    from technote.sphinxconf import *  # noqa: F403
except (ConfigError, tomllib.TOMLDecodeError) as _technote_config_error:
    _fail_technote_config(_technote_config_error)

# Suppress warnings about deprecated features in future Sphinx versions.
# This is noise for users because Documenteer itself constrains the Sphinx
# version.
warnings.filterwarnings(
    "ignore",
    category=RemovedInNextVersionWarning,
)

with suppress(ValueError):
    # Remove the sphinxcontrib-bibtex extension so that we can add it back
    # in the proper order relative to documenteer.ext.githubbibcache.
    extensions.remove("sphinxcontrib.bibtex")  # noqa: F405

with suppress(ValueError):
    # Remove myst-parser if added by technote.sphinxconf so we can
    # add myst-nb.
    extensions.remove("myst_parser")  # noqa: F405


# Add the GitHub bibfile cache extension before sphinxcontrib-bibtex so
# that it can add bibfiles to the sphinxcontrib-bibtex configuration.
extensions.extend(  # noqa: F405
    [
        "myst_nb",  # enables MyST markdown and Jupyter Notebook parsing
        "documenteer.ext.jira",
        "documenteer.ext.lsstdocushare",
        "documenteer.ext.mockcoderefs",
        "documenteer.ext.remotecodeblock",
        "documenteer.ext.bibtex",
        "documenteer.ext.githubbibcache",
        "sphinxcontrib.bibtex",
        "documenteer.ext.diagrams",
        "sphinxcontrib.mermaid",
        "sphinx_prompt",
        "sphinx_design",
        "sphinxcontrib.youtube",
        "sphinx_sitemap",
        "documenteer.ext.linkcheckservice",
        "documenteer.ext.intersphinxcache",
    ]
)

# The source file suffixes for .md and .ipynb are automatically managed by
# myst-nb.
source_suffix = {
    ".rst": "restructuredtext",
}

html_static_path: list[str] = [
    get_asset_path("rubin-favicon-transparent-32px.png"),
    get_asset_path("rubin-favicon.svg"),
    get_asset_path("rubin-technote.css"),
    get_asset_path("rubin-technote.css.map"),
    get_asset_path("rsd-assets/rubin-imagotype-color-on-white-crop.svg"),
    get_asset_path("rsd-assets/rubin-imagotype-color-on-black-crop.svg"),
]
extend_static_paths_with_asset_extension(html_static_path, "woff2")

html_css_files = ["rubin-technote.css"]

# A list of paths that contain extra templates (or templates that overwrite
# builtin/theme-specific templates).
templates_path = [get_template_dir("technote")]


# Configurations for the technote theme.
html_theme_options = {
    "light_logo": "rubin-imagotype-color-on-white-crop.svg",
    "dark_logo": "rubin-imagotype-color-on-black-crop.svg",
    "logo_link_url": "https://www.lsst.io",
    "logo_alt_text": "Rubin Observatory logo",
}

# Enable mermaid code fences as the Mermaid directive.
myst_fence_as_directive = ["mermaid"]

# Exclude non-index.ipynb Jupyter Notebooks
extend_excludes_for_non_index_source(exclude_patterns, "ipynb")  # noqa: F405
extend_excludes_for_non_index_source(exclude_patterns, "md")  # noqa: F405
extend_excludes_for_non_index_source(exclude_patterns, "rst")  # noqa: F405

# Configure bibliography with the bib cache
documenteer_bibfile_cache_dir = ".technote/bibfiles"
documenteer_bibfile_github_repos = [
    {
        "repo": "lsst/lsst-texmf",
        "ref": "main",
        "bibfiles": [
            "texmf/bibtex/bib/lsst.bib",
            "texmf/bibtex/bib/lsst-dm.bib",
            "texmf/bibtex/bib/refs_ads.bib",
            "texmf/bibtex/bib/refs.bib",
            "texmf/bibtex/bib/books.bib",
        ],
    }
]
# Set up bibtex_bibfiles
# Automatically load local bibfiles in the root directory.
bibtex_bibfiles = [str(p) for p in Path.cwd().glob("*.bib")]

bibtex_default_style = "lsst_aa"
bibtex_reference_style = "author_year"

_id = T.metadata.id  # noqa: F405
if _id is not None:
    html_context["editions_url"] = (  # noqa: F405
        f"https://{_id.lower()}.lsst.io/v/"
    )

# A technote registered with a DOI is that DOI's landing page, and says so in
# its sidebar: the DOI as a resolvable link, and the BibTeX entry with a
# button that copies it (components/sidebar-citation.html). Both values come
# from this one object, which composes them from the technote's own metadata
# through documenteer.citations; the template composes nothing.
#
# The object, rather than the composed strings, is what goes into the context
# because a technote's title is not known yet: technote.ext.metadata copies
# the document's H1 into the metadata at html-page-context time, so the entry
# has to be composed when the template reads it. The DOI is known now, which
# is what decides whether the surface exists at all -- a technote without one
# publishes nothing and ships no script, and so builds exactly as it did
# before the surface existed.
_citation = TechnoteCitation(T.metadata)  # noqa: F405
html_js_files: list[str] = []
if _citation.doi_url is not None:
    html_context["documenteer_technote_citation"] = _citation  # noqa: F405
    # The same script the guide's citation surfaces use; it reads the entry
    # from the <pre> the component renders and removes the button where the
    # clipboard API is unavailable.
    html_static_path.append(get_asset_path("rubin-citation-copy.js"))
    html_js_files.append("rubin-citation-copy.js")

# Ook link-check service settings for documenteer.ext.linkcheckservice.
# Only the technote-derived settings are set here; the others keep the
# defaults registered by the extension. All of them are overridable in
# the technote's conf.py after the ``from documenteer.conf.technote
# import *`` line (e.g. ``documenteer_linkcheck_use_service = False``
# restores Sphinx's built-in linkcheck builder).
_canonical_url = T.toml.technote.canonical_url  # noqa: F405
documenteer_linkcheck_origin_base_url = get_technote_origin_base_url(
    canonical_url=str(_canonical_url) if _canonical_url else None,
    technote_id=_id,
)
documenteer_linkcheck_default_branch_name = (
    T.toml.technote.github_default_branch  # noqa: F405
)

nitpick_ignore_regex.extend(get_common_nitpick_ignore_regex())  # noqa: F405
nitpick_ignore.extend(get_common_nitpick_ignore())  # noqa: F405

# Configure sitemap.xml
sitemap_url_scheme = "{link}"
sitemap_show_lastmod = True
sitemap_excludes = [
    # These auto-generated pages aren't relevant in technotes, which are
    # meant to be single-page documents.
    "search.html",
    "genindex.html",
    "py-modindex.html",
]
