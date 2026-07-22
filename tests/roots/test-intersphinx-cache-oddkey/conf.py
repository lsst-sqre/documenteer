# Standalone Sphinx configuration whose intersphinx_mapping key contains a
# path separator, used to verify the intersphinxcache extension forms a
# filesystem-safe cache filename rather than raising out of config-inited.

extensions = [
    "sphinx.ext.intersphinx",
    "documenteer.ext.intersphinxcache",
]

intersphinx_mapping = {
    "proj/sub": ("https://example.com/project/", None),
}
