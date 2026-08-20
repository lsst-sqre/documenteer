# Minimal standalone Sphinx configuration for the linkcheckservice
# extension tests. Neither a documenteer.toml nor a technote.toml sits
# beside this conf.py, so the project is configured from conf.py
# directly and the extension's messages must name Sphinx config values
# rather than a TOML file the project does not have.

extensions = [
    "documenteer.ext.linkcheckservice",
]
