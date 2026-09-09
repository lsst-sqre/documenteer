# type: ignore
"""Build tests for the citation of a technote that declares no date.

Only a ``date_updated`` written in technote.toml dates a technote's citation.
The metadata cannot answer the question on its own: the ``technote`` package
stamps its ``date_updated`` with the build clock whenever the file omits the
field, and reading that would date most of the fleet's citations to the day
they were last built -- the displayed year and the BibTeX ``year`` churning on
every rebuild, and both disagreeing with the deliberately undated CITATION.cff
that ``documenteer technote sync-cff`` writes from the same file.

So a technote nothing dates is cited undated, everywhere it is cited, and
``documenteer.ext.citationdate`` reports it once per build. These tests build
the whole technote stack for each case the report distinguishes: a technote
with a DOI and no declared date, one that declares a date, and one with no DOI
at all.
"""

from __future__ import annotations

from datetime import UTC, datetime
from io import StringIO
from typing import Any

import pytest
from lxml import html
from sphinx.testing.util import SphinxTestApp

DOI_URL = "https://doi.org/10.71929/rubin/2570545"

TEXT = ".technote-article-citation__text"
BIBTEX_ENTRY = ".technote-sidebar-citation__bibtex-entry"

# The warning's type.subtype, as ``suppress_warnings`` spells it and as Sphinx
# appends it to the rendered message.
WARNING_NAME = "documenteer.citation_date"

# What documenteer.citations composes from
# tests/roots/test-technote-undated/technote.toml, with the title taken from
# the document's H1. Neither form carries a year; the BibTeX key is the
# technote's handle, which no date enters into.
CITATION_TEXT = (
    "Sick, Jonathan; Lovelace, Ada. Undated Technote Citation Test. "
    f"Vera C. Rubin Observatory. {DOI_URL}"
)
BIBTEX_ENTRY_TEXT = """@techreport{SQR-000,
    author = {Sick, Jonathan and Lovelace, Ada},
    title = {{Undated Technote Citation Test}},
    institution = {Vera C. Rubin Observatory},
    number = {SQR-000},
    doi = {10.71929/rubin/2570545},
    url = {https://sqr-000.lsst.io/}
}"""


def _text(element: html.HtmlElement) -> str:
    """Return an element's text content, with whitespace collapsed."""
    return " ".join(element.text_content().split())


def _build(app: SphinxTestApp) -> html.HtmlElement:
    """Build the technote and parse its page."""
    app.build()
    return html.fromstring((app.outdir / "index.html").read_text("utf-8"))


def _warnings(warning: StringIO) -> list[str]:
    """Return every warning the build logged."""
    return [
        line for line in warning.getvalue().splitlines() if "WARNING" in line
    ]


def _citation_warnings(warning: StringIO) -> list[str]:
    """Return the build's undated-citation warnings.

    A test root is copied to a throwaway directory that is no Git repository,
    so ``sphinx-last-updated-by-git`` always warns that it found no history
    there. Scoping to this extension's own warnings keeps that noise -- which
    says nothing about the technote configuration under test -- out of the
    assertions.
    """
    return [line for line in _warnings(warning) if WARNING_NAME in line]


@pytest.mark.sphinx(
    "html", testroot="technote-undated", srcdir="technote-undated"
)
def test_an_undated_technote_is_cited_without_a_year(
    app: SphinxTestApp,
) -> None:
    """A technote that declares no ``date_updated`` is cited with no year at
    all: the displayed citation loses its ``(YYYY)`` and the BibTeX entry
    carries no ``year`` field. The entry's key is the technote's handle, so it
    is unaffected either way.

    Losing the segment is the point. The alternative -- dating the citation
    from the metadata, or from ``date_created`` -- would state a year that is
    not the year the technote was published, in a sentence a reader is invited
    to copy into a bibliography.
    """
    doc = _build(app)

    (text,) = doc.cssselect(TEXT)
    (entry,) = doc.cssselect(BIBTEX_ENTRY)
    assert _text(text) == CITATION_TEXT
    assert entry.text_content() == BIBTEX_ENTRY_TEXT


@pytest.mark.sphinx(
    "html", testroot="technote-undated", srcdir="technote-undated-clock"
)
def test_the_citation_does_not_move_with_the_build_clock(
    app: SphinxTestApp, make_app: Any
) -> None:
    """Editing an undated technote and rebuilding it composes the same
    citation, because neither build reads the clock it ran under.

    The year of the build is the value that used to get in: ``technote``
    stamps it into the metadata's ``date_updated``, so a citation composed
    from the metadata was re-dated on every rebuild, and a technote published
    years ago was cited to the current year. Asserting that the year the build
    ran in appears nowhere in the entry is what pins that down; the two builds
    agreeing is what the reader of a stored BibTeX entry gets from it.
    """
    doc = _build(app)
    (entry,) = doc.cssselect(BIBTEX_ENTRY)
    citation = entry.text_content()

    # Touch the document so the second build re-renders it. Sphinx writes
    # nothing for a page it finds up to date, and a page it did not write
    # would carry the first build's citation whatever the second composed.
    (app.srcdir / "index.rst").touch()
    second = make_app("html", srcdir=app.srcdir)
    reread: list[str] = []
    second.connect(
        "source-read", lambda _app, docname, _source: reread.append(docname)
    )
    rebuilt = _build(second)
    (rebuilt_entry,) = rebuilt.cssselect(BIBTEX_ENTRY)

    assert reread == ["index"], (
        "the second build must re-render the page, or it asserts nothing "
        "about what that build composed"
    )
    assert str(datetime.now(tz=UTC).year) not in citation
    assert rebuilt_entry.text_content() == citation


@pytest.mark.sphinx(
    "html", testroot="technote-undated", srcdir="technote-undated-warning"
)
def test_the_build_reports_the_undated_technote_once(
    app: SphinxTestApp,
) -> None:
    """The build says what the page cannot: this technote is being cited
    undated, and ``date_updated`` in technote.toml is where the date belongs.

    Nothing on a rendered page says a citation lost its year -- every surface
    simply omits the segment it cannot compose -- so the build is the only
    place an author finds out.
    """
    app.build()

    (warning,) = _citation_warnings(app.warning)
    assert "no publication date" in warning
    assert "date_updated" in warning
    assert "technote.toml" in warning
    assert f"[{WARNING_NAME}]" in warning, (
        "the warning must carry a type.subtype so that a -W build can "
        "suppress it by name"
    )


@pytest.mark.sphinx(
    "html",
    testroot="technote-undated",
    srcdir="technote-undated-strict",
    # A test root is copied to a throwaway directory that is no Git
    # repository, so sphinx-last-updated-by-git always warns there. Silencing
    # it is what leaves the undated citation as the only thing this build can
    # fail on.
    confoverrides={"suppress_warnings": ["git"]},
    warningiserror=True,
)
def test_a_strict_build_fails_on_the_undated_technote(
    app: SphinxTestApp,
) -> None:
    """A ``-W`` build fails, so a technote repository that requires a
    warning-free build has to supply the date rather than publish an undated
    citation.

    ``sphinx-build`` exits with the application's status code, which is what
    makes ``-W`` a gate rather than a nag.
    """
    app.build()

    (warning,) = _citation_warnings(app.warning)
    assert _warnings(app.warning) == [warning], (
        "the undated citation must be the only thing this build warns "
        "about, or the status code below says nothing about it"
    )
    assert app.statuscode != 0


@pytest.mark.sphinx(
    "html",
    testroot="technote-undated",
    srcdir="technote-undated-suppressed",
    confoverrides={"suppress_warnings": [WARNING_NAME]},
)
def test_the_report_is_suppressible(app: SphinxTestApp) -> None:
    """A technote that has no date to give silences the report by name, so
    its ``-W`` build still passes. Rendering is unchanged either way.
    """
    app.build()

    assert not _citation_warnings(app.warning)


@pytest.mark.sphinx(
    "html",
    testroot="technote-citation",
    srcdir="technote-citation-dated-report",
)
def test_a_dated_technote_is_not_reported(app: SphinxTestApp) -> None:
    """A technote that declares ``date_updated`` is cited with that date's
    year and reported not at all, so a dated technote builds silently.
    """
    doc = _build(app)

    (text,) = doc.cssselect(TEXT)
    assert "(2025)." in _text(text)
    assert not _citation_warnings(app.warning)


@pytest.mark.sphinx(
    "html",
    testroot="technote-nocitation",
    srcdir="technote-nocitation-report",
)
def test_a_technote_without_a_doi_is_not_reported(
    app: SphinxTestApp,
) -> None:
    """A technote with no DOI publishes no citation surface, so there is no
    citation to be undated and nothing to report -- whatever its dates say.

    Most technotes are never registered with a DOI, which is why this silence
    matters more than any other case here.
    """
    app.build()

    assert not _citation_warnings(app.warning)
