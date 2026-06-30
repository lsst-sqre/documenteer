# type: ignore
"""Guide-build smoke test for the pydata-sphinx-theme 0.19 upgrade.

Builds a minimal site with the full user-guide stack
(``from documenteer.conf.guide import *``) and asserts two couplings that the
pydata-sphinx-theme 0.19 / FontAwesome 7 upgrade touches:

- ``documenteer.ext.lastmodified``'s "last updated" footer still renders in the
  article footer slot (``footer.bd-footer-article``), and
- the GitHub ``icon_links`` entry renders with a FontAwesome 7 class that
  actually resolves to a glyph. FA7 (bundled in pydata 0.18+) dropped the FA6
  ``fa-github-square`` alias, so the icon must use ``fa-square-github``.

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

    # The last-updated footer renders the overriding <time> component in the
    # article footer slot (the slot pydata empty-checks at priority 500).
    assert "This page was last modified on" in content
    times = doc.cssselect(
        "footer.bd-footer-article time.documenteer-last-modified"
    )
    assert len(times) == 1, "last-updated footer should render exactly once"
    assert times[0].get("datetime") == EXPECTED_ISO
    assert times[0].text_content().strip() == EXPECTED_DATE

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
    # glyph; FA7 dropped the FA6 ``fa-github-square`` alias.
    for link in github_links:
        icons = link.cssselect("i.fa-square-github")
        assert len(icons) == 1, (
            "GitHub icon should use the FontAwesome 7 fa-square-github class"
        )
    assert "fa-github-square" not in content, (
        "the FA6 fa-github-square name was dropped in FA7 and must not leak in"
    )
