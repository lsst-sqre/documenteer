"""Test documenteer.ext.redoc."""

from __future__ import annotations

import json

import pytest
from lxml import html
from sphinx.testing.util import SphinxTestApp


@pytest.mark.sphinx(
    "html",
    testroot="redoc",
)
def test_redoc(app: SphinxTestApp) -> None:
    """Test the Redoc extension."""
    app.build()
    assert (app.outdir / "index.html").exists()
    assert (app.outdir / "api.html").exists()

    # Parse the generated HTML content
    with (app.outdir / "api.html").open("r", encoding="utf-8") as f:
        content = f.read()

    # Parse HTML with lxml
    doc = html.fromstring(content)

    # Check if the Redoc CDN script is included
    redoc_scripts = doc.cssselect(
        'script[src*="cdn.redoc.ly/redoc/v2.5.0/bundles/redoc.standalone.js"]'
    )
    assert len(redoc_scripts) == 1, "Redoc CDN script should be present"

    # Check that the openapi-spec script tag exists and is populated
    spec_scripts = doc.cssselect('script[id="openapi-spec"]')
    assert len(spec_scripts) == 1, "OpenAPI spec script should be present"

    spec_script = spec_scripts[0]
    assert (
        spec_script.get("type") == "application/json"
    ), "Spec script should have JSON content type"

    # Parse the JSON content in the script tag
    spec_content = spec_script.text_content().strip()
    assert spec_content, "Spec script should have content"

    spec_data = json.loads(spec_content)
    assert spec_data.get("openapi") == "3.1.0", "Should contain OpenAPI 3.1.0"
    assert (
        spec_data.get("info", {}).get("title") == "Times Square"
    ), "Should contain Times Square title"

    # Check that we have the redoc container div instead of redoc element
    redoc_containers = doc.cssselect("div#redoc-container")
    assert (
        len(redoc_containers) == 1
    ), "Should have exactly one redoc container"

    # Check that the JavaScript initialization script exists
    init_scripts = doc.cssselect("script:not([src]):not([id])")
    assert len(init_scripts) >= 1, "Should have initialization script"

    # Find the script that contains Redoc.init
    init_script = None
    for script in init_scripts:
        script_content = script.text_content()
        if "Redoc.init" in script_content:
            init_script = script
            break

    assert init_script is not None, "Should have script with Redoc.init call"

    script_content = init_script.text_content()

    # Check that the script contains the expected configuration options
    assert (
        "hide-hostname" in script_content
    ), "hide-hostname should be in options"
    assert (
        "path-in-middle-panel" in script_content
    ), "path-in-middle-panel should be in options"

    # Check that Redoc.init is called with the right parameters
    assert (
        "Redoc.init(spec, options, document.getElementById('redoc-container'))"
        in script_content
    ), "Should call Redoc.init with spec, options, and container"
