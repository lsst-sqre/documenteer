# Minimal standalone Sphinx configuration for the intersphinxcache
# extension tests. The extension is registered explicitly here (preset
# registration is a separate task), alongside the stock intersphinx
# extension it augments.

extensions = [
    "sphinx.ext.intersphinx",
    "documenteer.ext.intersphinxcache",
]

intersphinx_mapping = {
    "testproj": ("https://example.com/project/", None),
}
