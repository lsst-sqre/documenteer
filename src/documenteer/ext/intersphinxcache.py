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

A client-side on-disk TTL avoids the Ook round-trip on rapid successive
builds: when the cached ``.inv`` file for a mapping entry already exists with
an mtime younger than ``documenteer_intersphinx_cache_disk_cache_ttl`` seconds
(default 600), it is reused as-is without contacting Ook. Setting the TTL to
``0`` disables this fast path so every build revalidates with Ook. The TTL
governs only the client-to-Ook hop; whether Ook's own cached copy is stale
relative to the origin remains Ook's concern.

When the TTL has expired and a cached inventory plus its ETag sidecar exist,
the revalidation is conditional: the ETag Ook returned is persisted next to
the ``.inv`` file as ``<name>-<hash>.inv.etag`` and sent back as an
``If-None-Match`` header. If Ook answers ``304 Not Modified`` the on-disk
bytes are reused with no body transferred, the file's mtime is refreshed to
restart the TTL window, and the mapping is rewritten to the local file. A
``200 OK`` replaces both the ``.inv`` file and its sidecar. Against an older
Ook that returns no ``ETag`` header the behavior is exactly the pre-ETag
path — a full download with no sidecar — and a ``200`` without an ETag clears
any stale sidecar.

The extension is a complete no-op when ``OOK_TOKEN`` is unset (forks, local
builds) or when disabled via ``documenteer_intersphinx_cache_use_service``.
Any per-inventory client error (unauthorized, unreachable, 5xx, 404,
timeout) leaves that mapping entry untouched so stock intersphinx fetches
the origin directly, and reports the fallback at INFO level naming the
inventory. INFO (not WARNING) is deliberate: Rubin docs builds run with
``-W`` (warnings-as-errors), so logging graceful service degradation as a
warning would fail the build, defeating the guarantee that an Ook outage
can never make a build worse than today. (This matches the linkcheck
service, which likewise logs service-side conditions at INFO.)
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import posixpath
import re
import time
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


def _is_cache_fresh(path: Path, ttl: int) -> bool:
    """Return whether a cached inventory file exists and its mtime is younger
    than ``ttl`` seconds.

    A missing file (or any stat error) is treated as not fresh so the caller
    revalidates with Ook.
    """
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return False
    return (time.time() - mtime) < ttl


def _etag_sidecar_path(inv_path: Path) -> Path:
    """Return the ETag sidecar path for a cached inventory file.

    The sidecar sits next to the ``.inv`` file with an added ``.etag``
    suffix (e.g. ``<name>-<hash>.inv.etag``) and holds the entity tag Ook
    returned for the cached bytes, used for ``If-None-Match`` revalidation.
    """
    return inv_path.with_name(inv_path.name + os.extsep + "etag")


def _read_etag(etag_path: Path) -> str | None:
    """Return the stored ETag for a cached inventory, or `None`.

    A missing or unreadable sidecar (or an empty one) yields `None` so the
    caller revalidates with a full request rather than a conditional one.
    """
    try:
        return etag_path.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def _store_etag(etag_path: Path, etag: str | None) -> None:
    """Persist (or clear) the ETag sidecar for a cached inventory.

    Writing the sidecar is best-effort: when ``etag`` is `None` (the server
    sent no ``ETag`` header) any stale sidecar is removed so a later build
    does not revalidate against a tag the current bytes never had. A
    filesystem error is swallowed because the inventory itself is already
    written; the only consequence is that the next build falls back to a full
    (unconditional) fetch, never a build failure.
    """
    try:
        if etag is None:
            etag_path.unlink(missing_ok=True)
        else:
            etag_path.write_text(etag, encoding="utf-8")
    except OSError:
        pass


def _revalidate_inventory(
    client: IntersphinxCacheClient,
    name: str,
    origin_url: str,
    inv_path: Path,
    etag_path: Path,
) -> str | None:
    """Fetch or revalidate one inventory and return the local path to map to.

    Sends ``If-None-Match`` only when both a cached inventory and its ETag
    sidecar exist, so a ``304`` can safely reuse the on-disk bytes. Returns
    the local file path to rewrite the mapping entry to, or `None` to leave
    the entry untouched (a client error or a cache write failure), so stock
    intersphinx fetches the origin directly and the build is never worse than
    without the service.
    """
    request_etag: str | None = None
    if inv_path.is_file() and etag_path.is_file():
        request_etag = _read_etag(etag_path)

    try:
        result = client.get_inventory(origin_url, etag=request_etag)
    except IntersphinxCacheError as e:
        # Reported at info (not warning) level so a warnings-as-errors
        # (``-W``) build does not fail on graceful service degradation (e.g.
        # Ook returning 404 for a not-yet-deployed endpoint), matching the
        # linkcheck-service precedent in ``linkcheckservice.py``.
        logger.info(
            "Could not prefetch the intersphinx inventory for %r from "
            "Ook (%s); falling back to a direct fetch of %s.",
            name,
            e,
            origin_url,
        )
        return None

    if result.not_modified:
        # 304 Not Modified: the on-disk bytes are current and no body was
        # transferred. Refresh the file's mtime to restart the TTL window
        # (best-effort; a failed refresh only means the next build
        # revalidates sooner) and map to the local file.
        with contextlib.suppress(OSError):
            os.utime(inv_path, None)
        return str(inv_path)

    content = result.content
    if content is None:
        # Defensive: a non-304 response always carries bytes. Treat an empty
        # payload as a fallback rather than writing a truncated inventory.
        return None
    try:
        inv_path.parent.mkdir(parents=True, exist_ok=True)
        inv_path.write_bytes(content)
    except OSError as e:
        # A filesystem error writing the cache leaves this entry untouched;
        # reported at info level for the same warnings-as-errors reason.
        logger.info(
            "Could not write the prefetched intersphinx inventory for "
            "%r to %s (%s); falling back to a direct fetch of %s.",
            name,
            inv_path,
            e,
            origin_url,
        )
        return None
    # Reconcile the ETag sidecar with the freshly written bytes: store the new
    # ETag, or clear any stale sidecar when the server sent none (older-server
    # graceful degradation).
    _store_etag(etag_path, result.etag)
    return str(inv_path)


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

    ttl = config.documenteer_intersphinx_cache_disk_cache_ttl

    for name, value in list(mapping.items()):
        if not isinstance(value, (tuple, list)) or len(value) != 2:
            # An unexpected entry shape is left for intersphinx to validate.
            continue
        target_uri, inv_location = value
        origin_url = _resolve_origin_inventory_url(target_uri, inv_location)
        if origin_url is None:
            continue

        inv_path = cache_dir / _inventory_filename(name)
        etag_path = _etag_sidecar_path(inv_path)
        if ttl > 0 and _is_cache_fresh(inv_path, ttl):
            # TTL fast path: the on-disk inventory is younger than the TTL, so
            # reuse it without contacting Ook at all. The mapping is rewritten
            # to the local path exactly as it would be after a fresh prefetch.
            # The TTL governs only this client-to-Ook hop; whether Ook's own
            # cached copy is stale relative to the origin remains Ook's
            # concern.
            mapping[name] = (target_uri, str(inv_path))
            continue

        # The TTL has expired (or there is no cached copy). Revalidate with
        # Ook; on success rewrite only the inventory location (the target URI
        # is left unchanged so resolved links still point at the upstream
        # site). A None result leaves the entry untouched as a fallback.
        local_path = _revalidate_inventory(
            client, name, origin_url, inv_path, etag_path
        )
        if local_path is not None:
            mapping[name] = (target_uri, local_path)


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
    app.add_config_value(
        "documenteer_intersphinx_cache_disk_cache_ttl", 600, ""
    )

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
