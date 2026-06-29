"""Tests for documenteer.ext.diagrams."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from lxml import html
from sphinx.testing.util import SphinxTestApp

import sphinx_diagrams
from documenteer.ext.diagrams import SphinxDiagram, setup

# A stub "PNG" written by the mocked renderer. The tests only check that the
# file is produced and referenced, so a valid PNG signature is enough.
_STUB_PNG = b"\x89PNG\r\n\x1a\nstub-diagram"

# The real-render test needs both the diagrams package and the graphviz `dot`
# binary; otherwise it is skipped so CI without them still passes.
_HAS_DIAGRAMS = importlib.util.find_spec("diagrams") is not None
_HAS_DOT = shutil.which("dot") is not None


def _make_fake_run(
    calls: list[str],
) -> Callable[..., subprocess.CompletedProcess[bytes]]:
    """Build a ``subprocess.run`` replacement that writes a stub PNG.

    The extension invokes the renderer as ``python - <stem> false`` with the
    image directory as the working directory, so the replacement writes
    ``<stem>.png`` into that directory and records the stem it was asked to
    render.
    """

    def fake_run(
        args: list[str], **kwargs: Any
    ) -> subprocess.CompletedProcess[bytes]:
        stem = args[2]
        cwd = Path(kwargs["cwd"])
        cwd.mkdir(parents=True, exist_ok=True)
        (cwd / f"{stem}.png").write_bytes(_STUB_PNG)
        calls.append(stem)
        return subprocess.CompletedProcess(args, 0, stdout=b"", stderr=b"")

    return fake_run


def _rendered_images(app: SphinxTestApp) -> set[str]:
    """Names of the diagram images rendered into the output's _images dir."""
    return {p.name for p in (app.outdir / "_images").glob("diagrams-*.png")}


@pytest.mark.sphinx("html", testroot="diagrams", srcdir="diagrams-main")
def test_diagrams(app: SphinxTestApp, monkeypatch: pytest.MonkeyPatch) -> None:
    """Both inline and external diagrams render to hashed PNG images."""
    calls: list[str] = []
    monkeypatch.setattr(
        "documenteer.ext.diagrams.subprocess.run", _make_fake_run(calls)
    )
    app.build()

    # The two diagrams (inline + external) were each rendered once.
    assert len(calls) == 2
    images = _rendered_images(app)
    assert len(images) == 2

    doc = html.fromstring((app.outdir / "index.html").read_text())
    imgs = doc.cssselect("div.diagrams img")
    assert len(imgs) == 2
    for img in imgs:
        src = img.get("src")
        assert src is not None
        assert src.startswith("_images/diagrams-")
        # The src is relative to the (root) HTML page, i.e. the output dir.
        assert (app.outdir / src).exists()


@pytest.mark.sphinx("html", testroot="diagrams", srcdir="diagrams-cache")
def test_cache_invalidation(
    app: SphinxTestApp, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Editing a diagram's source re-renders it; unchanged diagrams are cached.

    This is the bug the vendored extension fixes: because the output filename
    is a hash of the diagram source, changing the source yields a new filename
    that misses the on-disk cache and re-renders, while an untouched diagram
    keeps its filename and is served from cache.
    """
    calls: list[str] = []
    monkeypatch.setattr(
        "documenteer.ext.diagrams.subprocess.run", _make_fake_run(calls)
    )
    app.build()
    first_images = _rendered_images(app)
    assert len(first_images) == 2
    # Both diagrams rendered, in document order: inline first, external second.
    assert len(calls) == 2
    external_stem = calls[1]

    # Edit only the inline diagram's source and rebuild without cleaning.
    index = app.srcdir / "index.rst"
    index.write_text(
        index.read_text().replace("inline-pod", "edited-pod"),
        encoding="utf-8",
    )
    calls.clear()
    app.build()

    # Only the edited diagram re-rendered: a new hashed filename was produced.
    assert len(calls) == 1
    second_images = _rendered_images(app)
    assert second_images - first_images == {f"{calls[0]}.png"}
    # The unchanged external diagram was served from cache (not re-rendered),
    # and its hashed image is still present.
    assert external_stem not in calls
    assert f"{external_stem}.png" in second_images


@pytest.mark.skipif(
    not (_HAS_DIAGRAMS and _HAS_DOT),
    reason="requires the diagrams package and the graphviz dot binary",
)
@pytest.mark.sphinx("html", testroot="diagrams", srcdir="diagrams-real")
def test_diagrams_real_render(app: SphinxTestApp) -> None:
    """End-to-end render with the real diagrams package and graphviz."""
    app.build()
    images = list((app.outdir / "_images").glob("diagrams-*.png"))
    assert len(images) == 2
    for image in images:
        assert image.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_back_compat_shim() -> None:
    """The legacy ``sphinx_diagrams`` module re-exports the vendored API."""
    assert sphinx_diagrams.SphinxDiagram is SphinxDiagram
    assert sphinx_diagrams.setup is setup
