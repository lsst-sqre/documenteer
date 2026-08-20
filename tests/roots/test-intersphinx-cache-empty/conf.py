# Standalone Sphinx configuration with an empty intersphinx mapping, used to
# check that the intersphinxcache extension no-ops (and logs no summary
# block) when there is nothing to prefetch.

extensions = [
    "sphinx.ext.intersphinx",
    "documenteer.ext.intersphinxcache",
]

intersphinx_mapping: dict[str, tuple[str, None]] = {}
