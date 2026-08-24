# type: ignore
"""Build tests for the DOI landing-page metadata a user guide emits in its
``<head>``.

DataCite asks that a DOI's landing page carry the DOI in machine-readable
form, so the guide's ``layout.html`` override emits Highwire ``citation_doi``
and Dublin Core ``DC.identifier`` meta tags for the site's own citation
alongside a schema.org JSON-LD block describing it and the works it cites.
Everything comes from the ``html_context`` the guide preset populates from
``[[project.citations]]``; nothing here composes a citation itself.

These tests build the full user-guide stack twice — once for a site that
declares citations and once for one that declares none — because the emitted
head is the only place the coupling between the configuration and the template
can be observed.
"""

from __future__ import annotations

import importlib.util
import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from lxml import html
from sphinx.testing.util import SphinxTestApp

# Must match the [[project.citations]] entries in
# tests/roots/test-guide/documenteer.toml. The self entry's DOI is written
# there as a https://doi.org/ URL and normalized on load.
SELF_DOI = "10.71929/rubin/2570308"
DATASET_DOI = "10.5281/zenodo.10385500"
# Must match project.base_url in that same file. Pydantic's HttpUrl gives the
# bare origin a trailing slash.
SITE_URL = "https://example.lsst.io/"

# The citation JSON-LD block's own selector. The head carries a second
# application/ld+json block -- documenteer.ext.lastmodified's per-page WebPage
# freshness statement -- so the citation block is addressed by its id.
CITATION_JSONLD = '#documenteer-citation-metadata[type="application/ld+json"]'

_HAS_PYDATA = importlib.util.find_spec("pydata_sphinx_theme") is not None

pytestmark = pytest.mark.skipif(
    not _HAS_PYDATA, reason="pydata_sphinx_theme is not installed"
)


def _mock_git_repository() -> MagicMock:
    """Build a mock GitRepository reporting a fixed commit date.

    The test root is copied to a throwaway srcdir that is not its own Git
    repository, so the real GitRepository would find no history.
    """
    mock_repo = MagicMock()
    mock_repo.is_shallow = False
    mock_repo.compute_last_modified.return_value = datetime(
        2024, 6, 1, tzinfo=UTC
    )
    return mock_repo


def _build(app: SphinxTestApp) -> html.HtmlElement:
    """Build the site and parse its index page."""
    with patch(
        "documenteer.ext.lastmodified.GitRepository",
        return_value=_mock_git_repository(),
    ):
        app.build()
    return html.fromstring(
        (app.outdir / "index.html").read_text(encoding="utf-8")
    )


@pytest.mark.sphinx("html", testroot="guide", srcdir="guide-head-citations")
def test_head_carries_the_self_doi(app: SphinxTestApp) -> None:
    """The self citation's DOI is emitted as Highwire and Dublin Core meta
    tags: bare for ``citation_doi``, and as the resolvable URL DataCite asks a
    landing page to display for ``DC.identifier``.
    """
    doc = _build(app)

    (citation_doi,) = doc.cssselect('head meta[name="citation_doi"]')
    assert citation_doi.get("content") == SELF_DOI
    (dc_identifier,) = doc.cssselect('head meta[name="DC.identifier"]')
    assert dc_identifier.get("content") == f"https://doi.org/{SELF_DOI}"


@pytest.mark.sphinx("html", testroot="guide", srcdir="guide-head-citations")
def test_head_carries_schema_org_jsonld(app: SphinxTestApp) -> None:
    """The head carries one JSON-LD block whose subject is the site: a node
    identified by the self DOI, with the guide's other citations hanging off
    it as schema.org ``citation`` values.
    """
    doc = _build(app)

    (script,) = doc.cssselect(f"head script{CITATION_JSONLD}")
    payload = json.loads(script.text_content())

    assert payload["@context"] == "https://schema.org"
    assert payload["@type"] == "WebSite"
    assert payload["@id"] == f"https://doi.org/{SELF_DOI}"
    assert payload["identifier"] == {
        "@type": "PropertyValue",
        "propertyID": "DOI",
        "value": SELF_DOI,
        "url": f"https://doi.org/{SELF_DOI}",
    }
    assert payload["name"] == "Guide Build Smoke Test"
    assert payload["url"] == SITE_URL
    assert payload["datePublished"] == "2025-06-30"

    # The "Dataset"-labelled citation crosswalks to a schema.org Dataset, with
    # its authors carrying resolvable ROR and ORCID identifiers -- the ORCID
    # is written bare in documenteer.toml and resolved to a URL here.
    (dataset,) = payload["citation"]
    assert dataset["@type"] == "Dataset"
    assert dataset["@id"] == f"https://doi.org/{DATASET_DOI}"
    assert dataset["creator"] == [
        {
            "@type": "Organization",
            "@id": "https://ror.org/048g3cy84",
            "name": "Vera C. Rubin Observatory",
        },
        {
            "@type": "Person",
            "@id": "https://orcid.org/0000-0003-3001-676X",
            "name": "Jonathan Sick",
            "affiliation": {
                "@type": "Organization",
                "name": "Rubin Observatory",
            },
        },
    ]


@pytest.mark.sphinx("html", testroot="guide", srcdir="guide-head-citations")
def test_jsonld_escapes_a_title_with_markup(app: SphinxTestApp) -> None:
    """A title containing an ampersand survives the round trip into the
    ``<script>`` block without being written as a raw character that could
    close the element or be misread as an entity.
    """
    doc = _build(app)

    (script,) = doc.cssselect(f"head script{CITATION_JSONLD}")
    raw = script.text_content()
    assert "<" not in raw
    assert ">" not in raw
    assert "&" not in raw

    (dataset,) = json.loads(raw)["citation"]
    assert dataset["name"] == "Smoke Test Images & Catalogs"


@pytest.mark.sphinx(
    "html", testroot="guide-nocitations", srcdir="guide-nocitations"
)
def test_guide_without_citations_emits_nothing(app: SphinxTestApp) -> None:
    """A guide that declares no [[project.citations]] adds no citation meta
    tags and no JSON-LD to its head.
    """
    doc = _build(app)

    assert not doc.cssselect('head meta[name="citation_doi"]')
    assert not doc.cssselect('head meta[name="DC.identifier"]')
    assert not doc.cssselect(f"head script{CITATION_JSONLD}")
    assert "documenteer_citations" not in app.config.html_context
