"""Sphinx configuration for Rubin technotes."""

from technote.sphinxconf import *  # noqa: F401 F403

from documenteer.conf import get_asset_path, get_template_dir

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
