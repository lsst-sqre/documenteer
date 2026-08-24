# type: ignore
"""Guide-build smoke test for the pydata-sphinx-theme 0.19 upgrade.

Builds a minimal site with the full user-guide stack
(``from documenteer.conf.guide import *``) and asserts two couplings that the
pydata-sphinx-theme 0.19 / FontAwesome 7 upgrade touches:

- ``documenteer.ext.lastmodified``'s "last updated" timestamp renders inside
  the "Help improve this page" box, which the ``components/prev-next.html``
  override places just below the prev/next links inside the article
  container, and
- the GitHub ``icon_links`` entry renders with a FontAwesome 7 class that
  actually resolves to a glyph. FA7 (bundled in pydata 0.18+) dropped the FA6
  ``fa-github-square`` alias; the icon uses the round ``fa-github`` mark,
  which matches the visual weight of the theme's other header icons.

Purely-visual aspects (the switcher dropdown, dark/light toggle, search) stay
in manual QA; this test pins the two couplings that can regress silently into a
clean build.
"""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from lxml import html
from sphinx.testing.util import SphinxTestApp

FIXED_DATE = datetime(2024, 6, 1, tzinfo=UTC)
# The ISO 8601 form of FIXED_DATE, as emitted into the <time datetime="...">.
EXPECTED_ISO = "2024-06-01T00:00:00+00:00"
# The UTC date as YYYY-MM-DD, the no-JavaScript visible footer fallback.
EXPECTED_DATE = "2024-06-01"
# Must match project.github_url in tests/roots/test-guide/documenteer.toml.
GITHUB_URL = "https://github.com/lsst-sqre/documenteer"
# The bare form of the [[project.citations]] DOI in that same file, which is
# written there as a https://doi.org/ URL and normalized on load.
CITATION_DOI = "10.71929/rubin/2570308"

# Whether pydata-sphinx-theme is importable. The guide stack pins
# ``html_theme = "pydata_sphinx_theme"``, so the build errors during fixture
# setup if the theme isn't installed -- skip before the ``app`` fixture builds.
_HAS_PYDATA = importlib.util.find_spec("pydata_sphinx_theme") is not None


def _mock_git_repository() -> MagicMock:
    """Build a mock GitRepository that always reports a fixed commit date.

    The test root is copied to a throwaway srcdir that is not its own Git
    repository, so the real GitRepository would find no history. Mocking it
    keeps the rendered last-updated date deterministic.
    """
    mock_repo = MagicMock()
    mock_repo.is_shallow = False
    mock_repo.compute_last_modified.return_value = FIXED_DATE
    return mock_repo


@pytest.mark.skipif(
    not _HAS_PYDATA, reason="pydata_sphinx_theme is not installed"
)
@pytest.mark.sphinx("html", testroot="guide", srcdir="guide-smoke")
def test_guide_build_smoke(app: SphinxTestApp) -> None:
    """The guide stack renders the last-updated footer and GitHub icon link."""
    mock_repo = _mock_git_repository()
    with patch(
        "documenteer.ext.lastmodified.GitRepository", return_value=mock_repo
    ):
        app.build()

    content = (app.outdir / "index.html").read_text(encoding="utf-8")
    doc = html.fromstring(content)

    # The last-updated timestamp renders the overriding <time> component
    # inside the "Help improve this page" box, which the prev-next component
    # override appends below the prev/next links inside the article container
    # (keeping it aligned with the article column in every sidebar layout).
    assert "This page was last modified on" in content
    times = doc.cssselect(
        "footer.prev-next-footer aside.rubin-improve-this-page "
        "time.documenteer-last-modified"
    )
    assert len(times) == 1, "last-updated timestamp should render exactly once"
    assert times[0].get("datetime") == EXPECTED_ISO
    assert times[0].text_content().strip() == EXPECTED_DATE

    # The theme's edit-this-page component must no longer render in the
    # secondary sidebar; the edit link's home is the "Help improve this page"
    # box. (In this test the srcdir is not a Git checkout, so githubeditlink
    # disables the edit link entirely and the box carries only the timestamp.)
    assert not doc.cssselect(".bd-sidebar-secondary .editthispage"), (
        "edit-this-page should be removed from the secondary sidebar"
    )

    # The print-only provenance footer renders in the article-footer slot
    # with its own copy of the <time> component and the canonical page URL.
    # (The interactive box sits inside the theme's d-print-none prev-next
    # footer, so printed pages rely on this footer instead.)
    print_footers = doc.cssselect(
        "footer.bd-footer-article .rubin-print-footer"
    )
    assert len(print_footers) == 1, "print footer should render exactly once"
    print_times = print_footers[0].cssselect("time.documenteer-last-modified")
    assert len(print_times) == 1
    assert print_times[0].get("datetime") == EXPECTED_ISO
    # Must match project.base_url in tests/roots/test-guide/documenteer.toml.
    assert (
        "https://example.lsst.io/index.html" in print_footers[0].text_content()
    ), "print footer should carry the canonical page URL"

    # A page bearing the hide_content_footer metadata field suppresses the
    # box and its print counterpart entirely, even though their timestamp
    # context is populated.
    hidden = html.fromstring(
        (app.outdir / "hidden.html").read_text(encoding="utf-8")
    )
    assert not hidden.cssselect("aside.rubin-improve-this-page"), (
        "hide_content_footer metadata should suppress the box"
    )
    assert not hidden.cssselect(".rubin-print-footer"), (
        "hide_content_footer metadata should suppress the print footer"
    )

    # The GitHub icon_links entry renders in the navbar icon-links list (not in
    # .navbar-nav -- the icon-links moved to navbar-header-items__end in 0.18,
    # which is why the old .navbar-nav i sizing rule is no longer needed). The
    # theme renders the list twice (desktop header + responsive sidebar), so
    # there is one link per copy.
    github_links = doc.cssselect(
        f'ul.navbar-icon-links a[href="{GITHUB_URL}"]'
    )
    assert github_links, "GitHub icon_links link should be present"

    # Every rendered copy must use the FontAwesome 7 class that resolves to a
    # glyph: the round fa-github mark, whose visual weight matches the
    # theme's other header icons (the square mark renders oversized).
    for link in github_links:
        icons = link.cssselect("i.fa-github")
        assert len(icons) == 1, (
            "GitHub icon should use the round fa-github class"
        )
    assert "fa-github-square" not in content, (
        "the FA6 fa-github-square name was dropped in FA7 and must not leak in"
    )
    assert "fa-square-github" not in content, (
        "the square GitHub mark renders oversized next to the other header "
        "icons and should not be used"
    )

    # The site's [[project.citations]] entry is resolved into html_context,
    # which is the whole contract the citation surfaces (head metadata, the
    # citation-card directive, the footer) read from.
    citations = app.config.html_context["documenteer_citations"]
    assert len(citations) == 1
    citation = citations[0]
    assert citation["label"] == "Site"
    assert citation["is_self"] is True
    assert citation["in_footer"] is True
    assert citation["note"] == "Cite this documentation."
    assert citation["doi"] == CITATION_DOI
    assert citation["doi_url"] == f"https://doi.org/{CITATION_DOI}"
    assert citation["plain_text"] == (
        "Vera C. Rubin Observatory (2025). Guide Build Smoke Test. "
        f"Vera C. Rubin Observatory. https://doi.org/{CITATION_DOI}"
    )
    assert f"doi = {{{CITATION_DOI}}}" in citation["bibtex"]
    assert app.config.html_context["documenteer_self_citation"] is citation
