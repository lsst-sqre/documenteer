"""Shared fixtures for the documenteer.ext test suite."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

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


# A test root whose documenteer.toml or technote.toml is deliberately invalid
# does not fail its build: the presets print the message and end the process
# with os._exit, which takes this whole pytest session down with status 2 and
# no traceback. Build such a root either in a subprocess (as
# tests/config_error_exit_test.py does) or inside
# ``documenteer.conf.raising_config_errors()``, which puts the ConfigError
# back in place of the exit.


def _evict_config_modules() -> None:
    """Drop the cached Sphinx config preset modules from ``sys.modules``."""
    for name in _CONFIG_MODULES:
        sys.modules.pop(name, None)


@pytest.fixture
def evict_config_modules() -> Callable[[], None]:
    """Return a callable that drops the cached config preset modules.

    A test that builds twice within one test function calls this between the
    builds, so the second build re-reads its configuration file rather than
    re-binding the settings the first build already computed — which is what
    makes such a test say anything about what the second build resolved.
    """
    return _evict_config_modules


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
    _evict_config_modules()
