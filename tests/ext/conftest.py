"""Shared fixtures for the documenteer.ext test suite."""

from __future__ import annotations

import sys

import pytest


@pytest.fixture(autouse=True)
def _fresh_guide_config_module() -> None:
    """Drop the cached guide config module before each test.

    ``documenteer.conf.guide`` computes all of its Sphinx settings at import
    time from the ``documenteer.toml`` in the current working directory. Once
    a test root's ``conf.py`` runs ``from documenteer.conf.guide import *``,
    Python caches the module in ``sys.modules``, so a *second* test root that
    builds the guide stack in the same pytest process would re-bind the first
    root's already-computed settings instead of reading its own
    ``documenteer.toml``. Evicting the module here makes every guide-stack
    build re-import it against its own config. The pop is a no-op for tests
    that never import the module.
    """
    sys.modules.pop("documenteer.conf.guide", None)
