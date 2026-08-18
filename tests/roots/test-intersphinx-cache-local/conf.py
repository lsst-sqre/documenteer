# Standalone Sphinx configuration mixing a remote intersphinx project with
# two entries the intersphinxcache extension must leave alone: one whose
# target URI is a local directory, and one whose inventory location is
# already a local file path. Both point at the ``objects.inv`` checked in
# beside this file, so stock intersphinx loads them without reaching the
# network.

from pathlib import Path

_here = Path(__file__).parent
_local_inventory = str(_here / "objects.inv")

extensions = [
    "sphinx.ext.intersphinx",
    "documenteer.ext.intersphinxcache",
]

intersphinx_mapping = {
    "remoteproj": ("https://example.com/project/", None),
    "localtarget": (f"{_here}/", None),
    "localinv": ("https://example.org/other/", _local_inventory),
}
