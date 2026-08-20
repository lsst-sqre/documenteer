# Standalone Sphinx configuration for a *technote*-shaped project: a
# technote.toml sits beside this conf.py, which is what
# documenteer.conf._configsource.detect_config_source keys on when the
# intersphinxcache extension words its permanent-redirect notice. The
# technote preset itself is not loaded here — its registration of the
# extension is covered by test_technote_preset_registers_extension — so this
# root stays a fast, dependency-free way to exercise that wording.

extensions = [
    "sphinx.ext.intersphinx",
    "documenteer.ext.intersphinxcache",
]

# A real instance: this inventory URL 301s to
# pydantic.dev/docs/validation/latest/objects.inv. The request is answered
# from a mocked response in the tests; nothing here reaches the network.
intersphinx_mapping = {
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
}
