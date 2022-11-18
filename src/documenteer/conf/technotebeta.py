"""Sphinx configuration for Rubin technotes (beta)."""

from typing import List

from technote.sphinxconf import *  # noqa: F401 F403

from documenteer.conf import get_asset_path, get_template_dir

html_static_path: List[str] = [
    get_asset_path("rubin-favicon-transparent-32px.png"),
    get_asset_path("rubin-favicon.svg"),
    get_asset_path("styles/rubin-technote.css"),
    get_asset_path("styles/rubin-technote.css.map"),
]

html_css_files = ["rubin-technote.css"]

# A list of paths that contain extra templates (or templates that overwrite
# builtin/theme-specific templates).
templates_path = [get_template_dir("technote")]
