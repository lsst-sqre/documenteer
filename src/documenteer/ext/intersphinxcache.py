"""Sphinx extension that prefetches intersphinx inventories from Ook.

This extension prefetches each project's intersphinx object inventory from
Ook's inventory cache service and rewrites ``intersphinx_mapping`` to point
at the locally-written files, so documentation builds no longer depend on
third-party site availability.

It runs on ``config-inited`` before ``sphinx.ext.intersphinx`` validates and
normalizes the mapping. For each mapping entry it resolves the origin
``objects.inv`` URL (the target URI joined with ``objects.inv`` when the
inventory location is unset), fetches it from Ook, writes it to a file in the
build directory, and rewrites that entry's inventory location to the local
path. The target URI is left unchanged, so resolved links still point at the
real upstream site and stock intersphinx runs unmodified. (Rationale:
intersphinx cannot send an ``Authorization`` header to inventory URLs, but it
accepts local file paths as inventory locations.)

The extension is a complete no-op when ``OOK_TOKEN`` is unset (forks, local
builds) or when disabled via ``documenteer_intersphinx_cache_use_service``.
Any per-inventory client error (unauthorized, unreachable, 5xx, timeout)
leaves that mapping entry untouched so stock intersphinx fetches the origin
directly, and emits a warning naming the inventory. An Ook outage can never
make a build worse than today.
"""

from __future__ import annotations

import hashlib
import os
import posixpath
import re
from pathlib import Path
from typing import TYPE_CHECKING

from sphinx.util import logging

from ..storage.intersphinxcacheclient import (
    DEFAULT_BASE_URL,
    TOKEN_ENV_VAR,
    IntersphinxCacheClient,
    IntersphinxCacheError,
)
from ..version import __version__

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.config import Config
    from sphinx.util.typing import ExtensionMetadata

# TOKEN_ENV_VAR is re-exported from the storage client so the extension's
# public surface is unchanged while the constant has a single definition.
__all__ = ["TOKEN_ENV_VAR", "setup"]

logger = logging.getLogger(__name__)

INVENTORY_FILENAME = "objects.inv"
"""Default inventory file name, appended to a target URI when the inventory
location is unset (mirrors ``sphinx.ext.intersphinx``)."""

CACHE_DIRNAME = ".documenteer_intersphinx_inventory"
"""Name of the build-directory subdirectory that holds prefetched
inventories. Dot-prefixed so it is excluded from a published site even when
the doctree cache defaults to ``outdir/.doctrees`` (a build without ``-d``),
mirroring how ``.doctrees`` is conventionally excluded."""

_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]")
"""Characters not allowed in a generated inventory filename stem."""


def _inventory_filename(name: str) -> str:
    """Return a filesystem-safe ``.inv`` filename for a mapping key.

    The mapping key comes from an author-controlled ``intersphinx_mapping``
    and may contain path separators or other characters that are unsafe in a
    filename. The key is sanitized for readability and suffixed with a short
    hash of the original key so distinct keys that sanitize to the same stem
    do not collide.
    """
    safe = _UNSAFE_FILENAME_CHARS.sub("_", name)
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:8]
    return f"{safe}-{digest}{os.extsep}inv"


def _resolve_origin_inventory_url(
    target_uri: str, inv_location: object
) -> str | None:
    """Resolve the origin ``objects.inv`` URL to prefetch for a mapping entry.

    Returns the URL to fetch from Ook, or `None` when the entry should be
    left untouched (a local target, or an inventory location that is already
    a local path).
    """
    if not isinstance(target_uri, str) or "://" not in target_uri:
        # A local or malformed target URI is left to stock intersphinx.
        return None
    if inv_location is None:
        return posixpath.join(target_uri, INVENTORY_FILENAME)
    if isinstance(inv_location, str) and "://" in inv_location:
        # An explicit remote inventory URL is prefetched as given.
        return inv_location
    # A local inventory path (or an unsupported shape) is left untouched.
    return None


def _prefetch_inventories(app: Sphinx, config: Config) -> None:
    """Prefetch intersphinx inventories from Ook and rewrite the mapping.

    Runs on ``config-inited`` before ``sphinx.ext.intersphinx`` validates
    the mapping. No-ops when the service is disabled, when ``OOK_TOKEN`` is
    unset, or when there is nothing to prefetch.
    """
    if not config.documenteer_intersphinx_cache_use_service:
        return
    if not os.getenv(TOKEN_ENV_VAR):
        # Forks and local builds without the token fall back to stock
        # intersphinx behavior with no attempt to contact Ook.
        return
    mapping = config.intersphinx_mapping
    if not mapping:
        return

    client = IntersphinxCacheClient(
        base_url=config.documenteer_intersphinx_cache_service_url
    )
    # Written under the build tree (a sibling of the doctree cache) rather
    # than app.outdir. The directory name is dot-prefixed so that even when
    # doctreedir defaults to outdir/.doctrees (a build without -d) and this
    # sibling lands inside outdir, the prefetched .inv blobs are excluded
    # from the published HTML site, mirroring how .doctrees is excluded.
    cache_dir = Path(app.doctreedir).parent / CACHE_DIRNAME

    for name, value in list(mapping.items()):
        if not isinstance(value, (tuple, list)) or len(value) != 2:
            # An unexpected entry shape is left for intersphinx to validate.
            continue
        target_uri, inv_location = value
        origin_url = _resolve_origin_inventory_url(target_uri, inv_location)
        if origin_url is None:
            continue

        try:
            data = client.get_inventory(origin_url)
        except IntersphinxCacheError as e:
            # Any client error leaves this entry untouched so stock
            # intersphinx fetches the origin directly; the build is never
            # worse than without the service.
            logger.warning(
                "Could not prefetch the intersphinx inventory for %r from "
                "Ook (%s); falling back to a direct fetch of %s.",
                name,
                e,
                origin_url,
            )
            continue

        inv_path = cache_dir / _inventory_filename(name)
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            inv_path.write_bytes(data)
        except OSError as e:
            # A filesystem error writing the cache leaves this entry
            # untouched so stock intersphinx fetches the origin directly;
            # the build is never worse than without the service.
            logger.warning(
                "Could not write the prefetched intersphinx inventory for "
                "%r to %s (%s); falling back to a direct fetch of %s.",
                name,
                inv_path,
                e,
                origin_url,
            )
            continue
        # Rewrite only the inventory location; the target URI is left
        # unchanged so resolved links still point at the upstream site.
        mapping[name] = (target_uri, str(inv_path))


def setup(app: Sphinx) -> ExtensionMetadata:
    """Set up the intersphinxcache extension.

    Parameters
    ----------
    app
        The Sphinx application.

    Returns
    -------
    sphinx.util.typing.ExtensionMetadata
        Extension metadata for Sphinx.
    """
    # Connect at the default priority (500) so this runs before
    # sphinx.ext.intersphinx's validate_intersphinx_mapping (priority 800)
    # on the same config-inited event.
    app.connect("config-inited", _prefetch_inventories)

    app.add_config_value("documenteer_intersphinx_cache_use_service", True, "")
    app.add_config_value(
        "documenteer_intersphinx_cache_service_url", DEFAULT_BASE_URL, ""
    )

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
