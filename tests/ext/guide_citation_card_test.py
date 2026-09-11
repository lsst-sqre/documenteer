# type: ignore
"""Build test for the ``citation-card`` directive under the guide stack.

:file:`citationcard_test.py` pins the directive's behaviour against a
hand-built ``html_context``. This test closes the loop through the real
configuration: it builds the guide test root, whose ``documenteer.toml``
declares ``[[project.citations]]``, and asserts that the card the directive
renders carries the citation the preset composed from that file — which is
also what pins that the guide preset registers the extension at all.
"""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from lxml import html
from sphinx.testing.util import SphinxTestApp

# Must match the [[project.citations]] entries in
# tests/roots/test-guide/documenteer.toml.
SELF_DOI_URL = "https://doi.org/10.71929/rubin/2570308"
DATASET_DOI_URL = "https://doi.org/10.5281/zenodo.10385500"

CARD = ".documenteer-citation-card"
LABEL = ".documenteer-citation-card__label"
CITATION = ".documenteer-citation-card__citation"
NOTE = ".documenteer-citation-card__note"

_HAS_PYDATA = importlib.util.find_spec("pydata_sphinx_theme") is not None


def _text(element: html.HtmlElement) -> str:
    """Return the element's text content, with whitespace collapsed."""
    return " ".join(element.text_content().split())


@pytest.mark.skipif(
    not _HAS_PYDATA, reason="pydata_sphinx_theme is not installed"
)
@pytest.mark.sphinx("html", testroot="guide", srcdir="guide-citation-card")
def test_cards_render_the_configured_citations(app: SphinxTestApp) -> None:
    """The guide root's index page renders both of its declared citations:
    the ``self`` entry by default and the "Dataset" entry by label.
    """
    mock_repo = MagicMock()
    mock_repo.is_shallow = False
    mock_repo.compute_last_modified.return_value = datetime(
        2024, 6, 1, tzinfo=UTC
    )
    with patch(
        "documenteer.ext.lastmodified.GitRepository", return_value=mock_repo
    ):
        app.build()

    doc = html.fromstring(
        (app.outdir / "index.html").read_text(encoding="utf-8")
    )

    self_card, dataset_card = doc.cssselect(CARD)

    assert _text(self_card.cssselect(LABEL)[0]) == "Site"
    assert _text(self_card.cssselect(CITATION)[0]) == (
        "Vera C. Rubin Observatory (2025). Guide Build Smoke Test. "
        f"Vera C. Rubin Observatory. {SELF_DOI_URL}"
    )
    assert self_card.cssselect(f"{CITATION} a")[0].get("href") == SELF_DOI_URL
    assert _text(self_card.cssselect(NOTE)[0]) == "Cite this documentation."

    assert _text(dataset_card.cssselect(LABEL)[0]) == "Dataset"
    # An ampersand in the title survives into the rendered card as text.
    assert "Smoke Test Images & Catalogs" in _text(
        dataset_card.cssselect(CITATION)[0]
    )
    assert (
        dataset_card.cssselect(f"{CITATION} a")[0].get("href")
        == DATASET_DOI_URL
    )
    assert _text(dataset_card.cssselect(NOTE)[0]) == (
        "Cite the dataset this guide documents."
    )
