# type: ignore
"""Build tests for the undated-citation warning under the guide preset.

``documenteer.ext.citationdate`` reports an undated citation against every
place its date could be set, and one of those places -- the
``[project.citation_defaults]`` table -- exists only for a site that wrote
one. Whether the site did is something only :file:`documenteer.toml` knows,
so the guide preset publishes it as the
``documenteer_citation_defaults_declared`` configuration value the extension
registers.

That handoff is the whole of what these tests pin. The extension's own tests
compose the citations directly and set the value with ``confoverrides``; here
the value comes from a real :file:`documenteer.toml`, through
``documenteer.conf.guide``, into a real build -- which is the only place a
preset that never set it, or set a name the extension does not read, would
show up.
"""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from sphinx.testing.util import SphinxTestApp

# The label of the lone [[project.citations]] entry in
# tests/roots/test-guide-citation-defaults/documenteer.toml, whose date the
# defaults table beside it does not supply.
UNDATED_LABEL = "Butler"
# The label of the dated self citation in tests/roots/test-guide, which
# declares no defaults table at all.
DATED_LABEL = "Site"

_HAS_PYDATA = importlib.util.find_spec("pydata_sphinx_theme") is not None

pytestmark = pytest.mark.skipif(
    not _HAS_PYDATA, reason="pydata_sphinx_theme is not installed"
)


def _warnings(app: SphinxTestApp) -> list[str]:
    """Build the site and return its warnings, one per line.

    The test root is copied to a throwaway srcdir that is not its own Git
    repository, so ``documenteer.ext.lastmodified``'s repository is mocked to
    report a fixed commit date rather than failing to find any history.
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
    return [
        line for line in app.warning.getvalue().splitlines() if line.strip()
    ]


@pytest.mark.sphinx(
    "html",
    testroot="guide-citation-defaults",
    srcdir="guide-citation-defaults",
)
def test_declared_defaults_table_reaches_the_warning(
    app: SphinxTestApp,
) -> None:
    """A site whose documenteer.toml writes [project.citation_defaults] is
    told it can date every entry there, not only in the entry the warning
    names.
    """
    (warning,) = [
        line for line in _warnings(app) if f"{UNDATED_LABEL!r}" in line
    ]

    assert "no publication date" in warning
    assert "[project.citation_defaults]" in warning
    assert "[[project.citations]]" in warning


@pytest.mark.sphinx(
    "html", testroot="guide", srcdir="guide-citation-date-no-defaults"
)
def test_a_site_without_the_table_is_not_told_about_it(
    app: SphinxTestApp,
) -> None:
    """A site whose entries each state their own fields hears nothing about a
    table it never wrote.

    Its citations are all dated, so what this pins is that the preset
    publishes the value for every site rather than only for the one that
    declared the table -- an unset value would leave the guide build reading
    whatever the extension defaulted to.
    """
    warnings = _warnings(app)

    assert not [line for line in warnings if "citation_defaults" in line]
    assert not [line for line in warnings if DATED_LABEL in line]
