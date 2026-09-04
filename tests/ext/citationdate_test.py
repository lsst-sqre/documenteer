# type: ignore
"""Tests for the undated-citation build warning.

A citation with no publication date is silently undated everywhere it is
shown: the plain text loses its ``(YYYY)``, the BibTeX entry loses its ``year``
field, and the BibTeX key is built from the author and title alone. Nothing
about the rendered page says so, and the date can be missing from either of two
places -- the ``[[project.citations]]`` entry, or the record of the
CITATION.cff file the entry reads -- so ``documenteer.ext.citationdate``
reports it while the environment is checked and names the one that applies.

The warning is emitted once per build, at ``env-check-consistency``, which
Sphinx runs only when a build actually read a document. Every test here
therefore gets an srcdir of its own: a build sharing another test's srcdir
would find nothing out of date and check no consistency.
"""

from __future__ import annotations

import pytest
from sphinx.testing.util import SphinxTestApp

# The warning's type.subtype, as ``suppress_warnings`` spells it and as Sphinx
# appends it to the rendered message.
WARNING_NAME = "documenteer.citation_date"

# Must match the citations in tests/roots/test-citationdate/conf.py.
DATED_LABEL = "Site"
INLINE_LABEL = "Dataset"
CFF_TOP_LEVEL_LABEL = "Software"
CFF_PREFERRED_TITLE = "The Rubin Observatory Data Butler"
CFF_PATH = "../CITATION.cff"


def _warnings(app: SphinxTestApp) -> list[str]:
    """Build the project and return its warnings, one per line."""
    app.build()
    return [
        line for line in app.warning.getvalue().splitlines() if line.strip()
    ]


def _warning_naming(app: SphinxTestApp, name: str) -> str:
    """Return the one warning naming this entry, so an assertion is scoped to
    the entry it is about rather than to the whole build's output.
    """
    (warning,) = [line for line in _warnings(app) if name in line]
    return warning


@pytest.mark.sphinx(
    "html", testroot="citationdate", srcdir="citationdate-inline"
)
def test_inline_entry_without_a_date_warns(app: SphinxTestApp) -> None:
    """An entry that states its own fields and no date is reported against
    the field of the entry itself, since that is the only place a date could
    be set.
    """
    warning = _warning_naming(app, f"{INLINE_LABEL!r}")

    assert "no publication date" in warning
    assert "date" in warning
    assert "[[project.citations]]" in warning
    # There is no file in the picture, so the fix must not offer one.
    assert "CITATION.cff" not in warning
    assert f"[{WARNING_NAME}]" in warning, (
        "the warning must carry a type.subtype so that a -W build can "
        "suppress it by name"
    )


@pytest.mark.sphinx(
    "html", testroot="citationdate", srcdir="citationdate-toplevel"
)
def test_cff_top_level_entry_names_that_record(app: SphinxTestApp) -> None:
    """An entry reading a CITATION.cff file's top-level record is reported
    against *that* record, named as the path the configuration wrote.

    Naming the record matters: a file whose top-level record has no date can
    still carry a dated preferred citation, and telling the author to date the
    wrong one would leave the citation exactly as undated as it was.
    """
    warning = _warning_naming(app, f"{CFF_TOP_LEVEL_LABEL!r}")

    assert "top-level record" in warning
    assert "preferred-citation" not in warning
    assert CFF_PATH in warning
    assert "date-released" in warning
    assert "year" in warning
    # The entry's own field is still an answer, and the one that needs no
    # change to a file the site may not own.
    assert "[[project.citations]]" in warning


@pytest.mark.sphinx(
    "html", testroot="citationdate", srcdir="citationdate-preferred"
)
def test_cff_preferred_entry_names_that_record(app: SphinxTestApp) -> None:
    """An entry reading a CITATION.cff file's preferred citation is reported
    against that record, and an entry with no label is named by its title.
    """
    warning = _warning_naming(app, f"{CFF_PREFERRED_TITLE!r}")

    assert "preferred-citation" in warning
    assert CFF_PATH in warning
    assert "date-released" in warning


@pytest.mark.sphinx(
    "html", testroot="citationdate", srcdir="citationdate-dated"
)
def test_dated_citation_is_not_reported(app: SphinxTestApp) -> None:
    """A citation that states a date is not reported, so a fully dated site
    builds silently.
    """
    warnings = _warnings(app)

    assert not [line for line in warnings if DATED_LABEL in line]
    # The three undated entries are, so the silence above is the date's doing
    # and not an inert extension.
    assert len([line for line in warnings if WARNING_NAME in line]) == 3


@pytest.mark.sphinx(
    "html",
    testroot="citationdate",
    srcdir="citationdate-suppressed",
    confoverrides={"suppress_warnings": [WARNING_NAME]},
)
def test_warning_is_suppressible(app: SphinxTestApp) -> None:
    """A site that accepts an undated citation silences the warning by name,
    so a warnings-as-errors build still passes.
    """
    assert not [
        line for line in _warnings(app) if "no publication date" in line
    ]
