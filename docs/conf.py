# See the documenteer.toml for overrides of the Rubin user guide presets

from documenteer.conf.guide import *  # noqa: F403

# The guide preset checks links with a 15 s timeout and two retries, which
# is enough for most sites but not for the archival hosts this guide cites
# (zenodo.org, datacite.org, ctan.org each timed out on dependabot docs
# jobs on 2026-10-13). Give them longer and one more try before failing.
linkcheck_timeout = 30
linkcheck_retries = 3
