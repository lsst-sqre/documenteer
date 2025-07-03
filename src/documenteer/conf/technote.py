"""Sphinx configuration for Rubin technotes."""

import warnings
from contextlib import suppress
from pathlib import Path

from sphinx.deprecation import RemovedInNextVersionWarning
from technote.sphinxconf import *  # noqa: F403

from documenteer.conf import (
    extend_excludes_for_non_index_source,
    extend_static_paths_with_asset_extension,
    get_asset_path,
    get_template_dir,
)

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
        "sphinx_diagrams",
        "sphinxcontrib.mermaid",
        "sphinx_prompt",
        "sphinx_design",
        "sphinxcontrib.youtube",
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
