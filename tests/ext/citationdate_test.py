# type: ignore
"""Tests for the undated-citation build warning.

A citation with no publication date is silently undated everywhere it is
shown: the plain text loses its ``(YYYY)``, the BibTeX entry loses its ``year``
field, and the BibTeX key is built from the author and title alone. Nothing
about the rendered page says so, and the date can be missing from either of two
places -- the ``[[project.citations]]`` entry, or the record of the
CITATION.cff file the entry reads -- so ``documenteer.ext.citationdate``
reports it as the builder is initialized and names the one that applies.

``builder-inited`` runs once on every build, whether or not that build reads a
document, which is what the last test here is about. The rest give each build
an srcdir of its own so that none of them inherits another's build state; the
rebuild test wants its own for the opposite reason, since its second build
reads the state its first left behind.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from sphinx.testing.util import SphinxTestApp

from documenteer.citations import (
    Citation,
    CitationType,
    GuideCitation,
    OrganizationAuthor,
    PartialDate,
)

if TYPE_CHECKING:
    from collections.abc import Callable

# The warning's type.subtype, as ``suppress_warnings`` spells it and as Sphinx
# appends it to the rendered message.
WARNING_NAME = "documenteer.citation_date"

# Must match the citations in tests/roots/test-citationdate/conf.py.
DATED_LABEL = "Site"
INLINE_LABEL = "Dataset"
CFF_TOP_LEVEL_LABEL = "Software"
CFF_PREFERRED_TITLE = "The Rubin Observatory Data Butler"
CFF_PATH = "../CITATION.cff"

# The label of the lone citation the rebuild test configures for itself, which
# it shares with none of the root's own citations.
REBUILD_LABEL = "Rebuilt"


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


RUBIN = OrganizationAuthor(name="Vera C. Rubin Observatory")
"""The author every composed citation credits, since none of the cases below
turns on who wrote the work.
"""

REPOSITORY_URL = "https://github.com/lsst/daf_butler"
"""A package's own repository, which is where a work with no DOI is located."""


def _undated(
    label: str,
    *,
    citation_type: CitationType | None = None,
    doi: str | None = None,
    url: str | None = None,
    cff: str | None = None,
    cff_preferred: bool = True,
    bibtex_key: str | None = None,
) -> GuideCitation:
    """Compose an undated citation stating only the fields that decide whether
    it is reported: what kind of work it is, whether it is located by a DOI or
    by a URL, and which record of a CITATION.cff file it reads.
    """
    return GuideCitation(
        citation=Citation(
            title=f"Undated {label}",
            type=citation_type,
            doi=doi,
            url=url,
            authors=(RUBIN,),
        ),
        label=label,
        cff=cff,
        cff_preferred=cff_preferred,
        bibtex_key=bibtex_key,
    )


def _context(*citations: GuideCitation) -> dict[str, Any]:
    """Compose the ``html_context`` of a site declaring exactly these
    citations, in the shape the guide preset publishes, replacing the test
    root's own.
    """
    return {
        "documenteer_citations": [
            citation.to_html_context() for citation in citations
        ]
    }


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
    srcdir="citationdate-url-software",
    confoverrides={
        "html_context": _context(
            _undated(
                "Software",
                citation_type=CitationType.software,
                url=REPOSITORY_URL,
            )
        )
    },
)
def test_url_located_software_is_not_reported(app: SphinxTestApp) -> None:
    """Software located by its repository rather than by a DOI is not
    reported, because a package released continuously has no publication event
    to date -- it is identified by its version and read at the date its reader
    accessed it.
    """
    assert not [line for line in _warnings(app) if WARNING_NAME in line]


@pytest.mark.sphinx(
    "html",
    testroot="citationdate",
    srcdir="citationdate-doi-software",
    confoverrides={
        "html_context": _context(
            _undated(
                "Software",
                citation_type=CitationType.software,
                doi="10.5281/zenodo.10385500",
            )
        )
    },
)
def test_doi_bearing_software_is_reported(app: SphinxTestApp) -> None:
    """Software deposited for a DOI is reported like any other work: DataCite
    requires a publication year of every DOI, so the date exists and only has
    to be written down.
    """
    assert "no publication date" in _warning_naming(app, "'Software'")


@pytest.mark.sphinx(
    "html",
    testroot="citationdate",
    srcdir="citationdate-shared-label",
    confoverrides={
        "html_context": _context(
            _undated(
                "TAP",
                doi="10.71929/rubin/3382539",
                bibtex_key="10.71929/rubin/3382539",
            ),
            _undated(
                "TAP",
                doi="10.71929/rubin/3382540",
                bibtex_key="10.71929/rubin/3382540",
            ),
        )
    },
)
def test_entries_sharing_a_label_are_named_by_key(
    app: SphinxTestApp,
) -> None:
    """Two entries under one label are each named by their key as well, so
    the two reports are told apart.

    A label may repeat -- it says what the reader needs to see at the spot
    the citation appears -- while the key is unique site-wide.
    """
    for key in ("10.71929/rubin/3382539", "10.71929/rubin/3382540"):
        warning = _warning_naming(app, f"'TAP' ({key})")
        assert "no publication date" in warning


@pytest.mark.sphinx(
    "html",
    testroot="citationdate",
    srcdir="citationdate-other-types",
    confoverrides={
        "html_context": _context(
            _undated(
                "Dataset",
                citation_type=CitationType.dataset,
                url="https://example.org/dataset",
            ),
            _undated(
                "Article",
                citation_type=CitationType.article,
                url="https://example.org/article",
            ),
            _undated(
                "Report",
                citation_type=CitationType.report,
                url="https://example.org/report",
            ),
        )
    },
)
def test_url_located_work_of_another_type_is_reported(
    app: SphinxTestApp,
) -> None:
    """The exemption is keyed on the work being software. Every other kind of
    work was published on a date whether or not it was deposited for a DOI, so
    being located by a URL says nothing about the date it is missing.
    """
    for label in ("Dataset", "Article", "Report"):
        assert "no publication date" in _warning_naming(app, f"{label!r}")


@pytest.mark.sphinx(
    "html",
    testroot="citationdate",
    srcdir="citationdate-untyped",
    confoverrides={
        "html_context": _context(_undated("Untyped", url=REPOSITORY_URL))
    },
)
def test_url_located_untyped_entry_is_reported(app: SphinxTestApp) -> None:
    """An entry that states no type says nothing about what the work is, so it
    is not the software the exemption is about, and a URL alone does not make
    it so.
    """
    assert "no publication date" in _warning_naming(app, "'Untyped'")


@pytest.mark.sphinx(
    "html",
    testroot="citationdate",
    srcdir="citationdate-preferred-software",
    confoverrides={
        "html_context": _context(
            _undated(
                "Preferred",
                citation_type=CitationType.software,
                url=REPOSITORY_URL,
                cff=CFF_PATH,
            )
        )
    },
)
def test_cff_preferred_software_is_reported(app: SphinxTestApp) -> None:
    """An entry reading a CITATION.cff file's preferred-citation is reported
    even when that record is software located by a URL, because the record the
    entry picked out is a work other than the repository the file describes.
    """
    assert "no publication date" in _warning_naming(app, "'Preferred'")


@pytest.mark.sphinx(
    "html",
    testroot="citationdate",
    srcdir="citationdate-exemplar",
    confoverrides={
        "html_context": _context(
            _undated(
                "Software",
                citation_type=CitationType.software,
                url=REPOSITORY_URL,
                cff=CFF_PATH,
                cff_preferred=False,
            ),
            GuideCitation(
                citation=Citation(
                    title="The Rubin Observatory Data Butler",
                    type=CitationType.article,
                    doi="10.1117/12.2629569",
                    authors=(RUBIN,),
                    date=PartialDate(2022),
                ),
                label="Paper",
                cff=CFF_PATH,
            ),
        )
    },
)
def test_package_site_reports_nothing(app: SphinxTestApp) -> None:
    """The shape a package site actually has reports nothing at all: an
    undated Software entry reading its own CITATION.cff top-level record,
    beside the dated Paper that file's preferred-citation names.

    This is what the exemption is for. Reporting the Software entry would make
    ``suppress_warnings`` such a site's end state, which would silence the
    Paper warning its author does want to hear.
    """
    assert not [line for line in _warnings(app) if WARNING_NAME in line]


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


def _one_citation_context(date: PartialDate | None) -> dict[str, Any]:
    """Compose the ``html_context`` of a site citing itself once, dated or
    not, in the shape the guide preset publishes.

    The rebuild test's two builds differ in this date and in nothing else, so
    the date is the whole of the configuration change the check has to notice.
    """
    context = GuideCitation(
        citation=Citation(
            title="Citation Date Rebuild Site",
            doi="10.71929/rubin/2570308",
            authors=(OrganizationAuthor(name="Vera C. Rubin Observatory"),),
            publisher="Vera C. Rubin Observatory",
            date=date,
        ),
        label=REBUILD_LABEL,
        is_self=True,
        is_preferred=True,
    ).to_html_context()
    return {
        "documenteer_citations": [context],
        "documenteer_self_citation": context,
        "documenteer_preferred_citation": context,
    }


@pytest.mark.sphinx(
    "html",
    testroot="citationdate",
    srcdir="citationdate-rebuild",
    confoverrides={
        "html_context": _one_citation_context(PartialDate(2025, 6))
    },
)
def test_rebuild_reading_no_document_still_warns(
    app: SphinxTestApp, make_app: Callable[..., SphinxTestApp]
) -> None:
    """Dropping a citation's date and rebuilding an already-built site is
    reported, even though the edit leaves every document up to date and so
    re-reads none of them.

    This is the ordinary local loop: an author edits documenteer.toml and
    rebuilds. Citations reach Sphinx through ``html_context``, whose
    ``rebuild`` is ``"html"``, which is why changing one costs the documents
    nothing. The assertion on ``env-check-consistency`` is what pins that
    down -- Sphinx skips that event on a build that read nothing, so a check
    connected to it would say nothing at all here.
    """
    app.build()

    assert not [line for line in _warnings(app) if WARNING_NAME in line], (
        "the first build states a date, so it must have nothing to report"
    )

    rebuilt = make_app(
        "html",
        srcdir=app.srcdir,
        confoverrides={"html_context": _one_citation_context(None)},
    )
    consistency_checks: list[object] = []
    rebuilt.connect(
        "env-check-consistency",
        lambda _app, env: consistency_checks.append(env),
    )
    warning = _warning_naming(rebuilt, f"{REBUILD_LABEL!r}")

    assert not consistency_checks, (
        "the rebuild must be one that re-reads no document, or it does not "
        "exercise the incremental case at all"
    )
    assert "no publication date" in warning
    assert f"[{WARNING_NAME}]" in warning
