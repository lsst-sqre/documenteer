# type: ignore
"""Double-build tests for a guide whose ``[[project.citations]]`` change.

A ``citation-card`` and a ``doi`` role resolve their entry while the document
is *read* and bake the rendered result into the doctree, where every other
citation surface — the ``<head>`` metadata, the JSON-LD, the footer — is
composed as the page is written. Sphinx re-reads a document only when a
configuration value registered with ``rebuild="env"`` changes, so the two
kinds of surface agree about an edited :file:`documenteer.toml` only if the
citations reach such a value.

That is what these tests pin, and they can only pin it across *two* builds
sharing one doctree directory: a single build reads everything anyway, so the
staleness these tests are about is invisible to it. Each test therefore copies
the test root to :file:`tmp_path`, builds it, edits the file, and builds again
over the warm cache the first build left.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from lxml import html

if TYPE_CHECKING:
    from collections.abc import Callable

    from sphinx.application import Sphinx
    from sphinx.testing.util import SphinxTestApp

TESTROOT = "test-guide-citation-rebuild"
"""The test root these tests copy, whose index page carries both read-time
citation surfaces."""

DATASET_DOI = "10.5281/zenodo.10385500"
"""The DOI of the "Dataset" entry in that root's documenteer.toml."""

EDITED_DOI = "10.5281/zenodo.10385599"
"""What the tests that edit the "Dataset" entry rewrite its DOI to."""

CARD_CITATION = ".documenteer-citation-card__citation"
"""The card's citation paragraph, whose trailing link is the entry's DOI."""

ROLE_SENTENCE = "Cite the images at"
"""The start of the index page's sentence holding the ``doi`` role."""

_HAS_PYDATA = importlib.util.find_spec("pydata_sphinx_theme") is not None

pytestmark = pytest.mark.skipif(
    not _HAS_PYDATA, reason="pydata_sphinx_theme is not installed"
)


@pytest.fixture
def srcdir(rootdir: Path, tmp_path: Path) -> Path:
    """Copy the citation-rebuild root to a throwaway source directory.

    The copy is what makes an edit possible: these tests rewrite
    :file:`documenteer.toml` between builds, and the doctree cache the first
    build leaves beside it has to be the one the second build reads.
    """
    srcdir = tmp_path / "guide-citation-rebuild"
    shutil.copytree(rootdir / TESTROOT, srcdir)
    return srcdir


def _build(
    make_app: Callable[..., SphinxTestApp], srcdir: Path
) -> tuple[SphinxTestApp, list[str]]:
    """Build the copied root over whatever doctree cache is already beside it,
    returning the application and the docnames the build re-read.

    ``source-read`` fires once per document Sphinx actually reads, so the
    returned list is empty for a build that found every document up to date —
    which is the whole question these tests ask.

    The guide preset computes its settings at import time from the
    :file:`documenteer.toml` in the working directory and Python caches the
    module, so it is evicted here: otherwise the second build's :file:`conf.py`
    would re-bind the *first* build's already-computed settings and no edit
    could ever be seen. The repository ``documenteer.ext.lastmodified`` looks
    for is mocked because the copied root is not one.
    """
    sys.modules.pop("documenteer.conf.guide", None)
    app = make_app("html", srcdir=srcdir)

    reread: list[str] = []

    def _note_read(app: Sphinx, docname: str, source: list[str]) -> None:
        reread.append(docname)

    app.connect("source-read", _note_read)

    mock_repo = MagicMock()
    mock_repo.is_shallow = False
    mock_repo.compute_last_modified.return_value = datetime(
        2024, 6, 1, tzinfo=UTC
    )
    with patch(
        "documenteer.ext.lastmodified.GitRepository", return_value=mock_repo
    ):
        app.build()

    # Releases the node, directive, and role registrations this build made, so
    # that the next application in this test registers them as a first build
    # would rather than warning that it is overriding them.
    app.cleanup()
    return app, reread


def _edit_toml(srcdir: Path, old: str, new: str) -> None:
    """Rewrite one passage of the copied documenteer.toml, failing loudly if
    the passage is no longer there to rewrite.
    """
    path = srcdir / "documenteer.toml"
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new), encoding="utf-8")


def _index(app: SphinxTestApp) -> html.HtmlElement:
    """Parse the built index page."""
    return html.fromstring(
        (app.outdir / "index.html").read_text(encoding="utf-8")
    )


def test_an_unchanged_config_re_reads_nothing(make_app, srcdir: Path) -> None:
    """A second build of an untouched site reads no document at all.

    This is the other half of the contract: the value the citations travel in
    is one every build recomputes, so a site that did not edit its citations
    must not pay for a full re-read on each build.
    """
    _, first = _build(make_app, srcdir)
    assert first == ["index"]

    _, second = _build(make_app, srcdir)
    assert second == []


def test_an_edited_citation_re_reads_the_documents(
    make_app, srcdir: Path
) -> None:
    """Dropping a citation's date re-reads every document, so the surfaces
    that resolved the citation as they were read resolve it again.
    """
    _build(make_app, srcdir)

    _edit_toml(srcdir, "date = 2025-01-15\n", "")

    _, reread = _build(make_app, srcdir)
    assert reread == ["index"]


def test_an_edited_citation_reaches_every_surface(
    make_app, srcdir: Path
) -> None:
    """Changing a citation's DOI changes it in the card and the role, which
    are composed as the page is read, as well as in the JSON-LD, which is
    composed as it is written.

    The three disagreeing is the defect this pins: before the citations
    reached an ``env`` configuration value, the block carried the edited DOI
    while the card and the role went on showing the one the previous build
    baked into the doctree.
    """
    _build(make_app, srcdir)

    _edit_toml(srcdir, DATASET_DOI, EDITED_DOI)

    app, _ = _build(make_app, srcdir)
    doc = _index(app)
    edited_url = f"https://doi.org/{EDITED_DOI}"

    card_link = doc.cssselect(f"{CARD_CITATION} a")[0]
    assert card_link.get("href") == edited_url

    role_paragraph = next(
        paragraph
        for paragraph in doc.cssselect("p")
        if paragraph.text_content().startswith(ROLE_SENTENCE)
    )
    assert role_paragraph.cssselect("a")[0].get("href") == edited_url

    # The page carries more than one JSON-LD block -- the page's own WebPage
    # node is another -- and the site's citations are the one that states a
    # ``citation`` relation.
    blocks = [
        json.loads(script.text_content())
        for script in doc.cssselect('script[type="application/ld+json"]')
    ]
    citations_block = next(block for block in blocks if "citation" in block)
    assert edited_url in json.dumps(citations_block)

    # Nothing anywhere on the page still shows the DOI the edit replaced.
    assert DATASET_DOI not in (app.outdir / "index.html").read_text(
        encoding="utf-8"
    )


def test_a_page_claim_is_checked_on_a_config_only_rebuild(
    make_app, srcdir: Path
) -> None:
    """A ``page`` claim added to documenteer.toml alone is checked on the
    rebuild that follows, rather than waiting for a fresh build.

    ``documenteer.ext.citationpage`` checks a claim as the environment is
    checked for consistency, which Sphinx runs only when a document was
    re-read — so this check reaching an edit that touched no document is a
    consequence of the citations invalidating the environment.
    """
    _build(make_app, srcdir)

    _edit_toml(
        srcdir, 'label = "Dataset"', 'label = "Dataset"\npage = "index#gone"'
    )

    app, _ = _build(make_app, srcdir)
    assert "is not an anchor on index" in app.warning.getvalue()
