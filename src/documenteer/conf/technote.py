"""Sphinx configuration for Rubin technotes."""

from pathlib import Path

from technote.sphinxconf import *  # noqa: F401 F403

from documenteer.conf import get_asset_path, get_template_dir

try:
    # Remove the sphinxcontrib-bibtex extension so that we can add it back
    # in the proper order relative to documenteer.ext.githubbibcache.
    extensions.remove("sphinxcontrib.bibtex")  # noqa: F405
except ValueError:
    pass

# Add the GitHub bibfile cache extension before sphinxcontrib-bibtex so
# that it can add bibfiles to the sphinxcontrib-bibtex configuration.
extensions.extend(  # noqa: F405
    [
        "documenteer.ext.jira",
        "documenteer.ext.lsstdocushare",
        "documenteer.ext.mockcoderefs",
        "documenteer.ext.remotecodeblock",
        "documenteer.ext.bibtex",
        "documenteer.ext.githubbibcache",
        "sphinxcontrib.bibtex",
    ]
)

html_static_path: list[str] = [
    get_asset_path("rubin-favicon-transparent-32px.png"),
    get_asset_path("rubin-favicon.svg"),
    get_asset_path("styles/rubin-technote.css"),
    get_asset_path("styles/rubin-technote.css.map"),
    get_asset_path("rsd-assets/rubin-imagotype-color-on-white-crop.svg"),
    get_asset_path("rsd-assets/rubin-imagotype-color-on-black-crop.svg"),
]

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
bibtex_bibfiles = []

# Automatically load local bibfiles in the root directory.
for p in Path.cwd().glob("*.bib"):
    bibtex_bibfiles.append(str(p))

bibtex_default_style = "lsst_aa"
bibtex_reference_style = "author_year"
