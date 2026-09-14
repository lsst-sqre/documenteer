from documenteer.conf.technote import *  # noqa: F401 F403

# This test root builds without network access, so the GitHub bibfile
# cache (which fetches lsst-texmf bibfiles at config-inited) is
# disabled by overriding the preset's default here in conf.py.
documenteer_bibfile_github_repos: list = []
