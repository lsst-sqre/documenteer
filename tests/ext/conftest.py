"""Shared fixtures for the documenteer.ext test suite."""

from __future__ import annotations

import sys

import pytest

# The Sphinx configuration presets compute every setting at import time from
# the configuration file in the current working directory, so a module left
# in sys.modules would re-bind one test root's settings for the next. The
# technote preset needs technote.sphinxconf evicted with it: that module holds
# the loaded technote.toml in its own module-level ``T``.
_CONFIG_MODULES = (
    "documenteer.conf.guide",
    "documenteer.conf.technote",
    "technote.sphinxconf",
)


@pytest.fixture(autouse=True)
def _fresh_config_modules() -> None:
    """Drop the cached Sphinx config preset modules before each test.

    Once a test root's ``conf.py`` runs ``from documenteer.conf.guide import
    *``, Python caches the module in ``sys.modules``, so a *second* test root
    that builds the same stack in the same pytest process would re-bind the
    first root's already-computed settings instead of reading its own
    ``documenteer.toml`` or ``technote.toml``. Evicting the modules here makes
    every build re-import them against their own configuration. The pops are
    no-ops for tests that never import them.
    """
    for name in _CONFIG_MODULES:
        sys.modules.pop(name, None)
