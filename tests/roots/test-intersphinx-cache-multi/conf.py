# Standalone Sphinx configuration with two intersphinx projects, used to
# exercise per-inventory fallback in the intersphinxcache extension.

extensions = [
    "sphinx.ext.intersphinx",
    "documenteer.ext.intersphinxcache",
]

intersphinx_mapping = {
    "proja": ("https://a.example.com/", None),
    "projb": ("https://b.example.com/", None),
}
