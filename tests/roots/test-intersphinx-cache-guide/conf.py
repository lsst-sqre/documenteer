# Standalone Sphinx configuration for a *guide*-shaped project: a
# documenteer.toml sits beside this conf.py, which is exactly what
# documenteer.conf._configsource.detect_config_source keys on when the
# intersphinxcache extension words its permanent-redirect notice. The guide
# preset itself is not loaded here — its registration of the extension is
# covered by test_guide_preset_registers_extension — so this root stays a
# fast, theme-free way to exercise that wording.

extensions = [
    "sphinx.ext.intersphinx",
    "documenteer.ext.intersphinxcache",
]

# Two real instances: the pydantic inventory URL has permanently moved
# (301 to pydantic.dev/docs/validation/latest/objects.inv), while the Python
# one has not. Both are answered from mocked responses in the tests; nothing
# here reaches the network.
intersphinx_mapping = {
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
    "python": ("https://docs.python.org/3/", None),
}
