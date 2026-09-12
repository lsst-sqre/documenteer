# type: ignore
"""Build tests for the date a technote's citation states.

A technote's citation date is its ``date_updated``: the value ``technote.toml``
declares, and otherwise the committer date of the commit the build was made
from. The ``technote`` package resolves the two into one field before
Documenteer composes anything, so every dated surface on the page -- the
sidebar's "Updated", the ``<head>`` metadata, the article-end citation, and
the BibTeX entry -- states the same date, and a rebuild of an unchanged commit
states it again.

These tests build the whole technote stack inside a real git repository, since
the commit date is only reachable from one. Each case is a technote with a
DOI: one that declares no ``date_updated``, one that declares one, and the
rebuild that has to agree with the first.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from lxml import html
from sphinx.testing.util import SphinxTestApp

TEXT = ".technote-article-citation__text"
BIBTEX_ENTRY = ".technote-sidebar-citation__bibtex-entry"

# The committer date of the commit every technote here is built from. Its year
# is not the current one, so a citation carrying the year of the build instead
# could never be mistaken for one carrying this; and it falls after the test
# root's ``date_created``, which a derived date is clamped to.
COMMIT_DATE = "2025-05-06T07:08:09+00:00"
COMMIT_YEAR = "2025"
COMMIT_MONTH = "May"

# A date declared in technote.toml, in a different year, so an assertion on
# the year says which of the two values the citation read.
DECLARED_DATE = "2019-11-14"
DECLARED_YEAR = "2019"

# The warning's type.subtype, as ``suppress_warnings`` spells it and as Sphinx
# appends it to the rendered message. No technote emits it any more.
WARNING_NAME = "documenteer.citation_date"


def _text(element: html.HtmlElement) -> str:
    """Return an element's text content, with whitespace collapsed."""
    return " ".join(element.text_content().split())


def _commit(srcdir: Path) -> None:
    """Make ``srcdir`` a git repository holding one commit of its contents.

    The identity and the dates are supplied here rather than taken from the
    machine, so the commit date these tests assert on is the one they set
    whoever runs them, and signing is switched off so a contributor's global
    ``commit.gpgsign`` cannot make the commit ask for a key.
    """
    env = os.environ | {
        "GIT_AUTHOR_DATE": COMMIT_DATE,
        "GIT_COMMITTER_DATE": COMMIT_DATE,
    }
    config = [
        "-c",
        "user.name=Technote Test",
        "-c",
        "user.email=technote@example.com",
        "-c",
        "commit.gpgsign=false",
    ]
    commands = [
        ["init", "--quiet", "--initial-branch=main", "."],
        ["add", "."],
        ["commit", "--quiet", "-m", "Add the technote"],
    ]
    for command in commands:
        subprocess.run(
            ["git", *config, *command], cwd=srcdir, check=True, env=env
        )


@pytest.fixture
def committed_technote(
    rootdir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Any:
    """Return a factory for a technote source tree committed to git.

    ``SOURCE_DATE_EPOCH`` is removed from the environment because ``technote``
    gives it precedence over the commit date, so a suite run under a
    reproducible-build wrapper would otherwise date these technotes from the
    wrapper rather than from the commit these tests make.
    """
    monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)

    def make(name: str, *, declared_date: str | None = None) -> Path:
        srcdir = tmp_path / name
        shutil.copytree(rootdir / "test-technote-undated", srcdir)
        if declared_date is not None:
            toml = srcdir / "technote.toml"
            toml.write_text(
                toml.read_text("utf-8").replace(
                    "[technote]\n",
                    f"[technote]\ndate_updated = {declared_date}\n",
                ),
                "utf-8",
            )
        _commit(srcdir)
        return srcdir

    return make


def _build(app: SphinxTestApp) -> html.HtmlElement:
    """Build the technote and parse its page."""
    app.build()
    return html.fromstring((app.outdir / "index.html").read_text("utf-8"))


def _warnings(app: SphinxTestApp) -> list[str]:
    """Return every warning the build logged."""
    return [
        line
        for line in app.warning.getvalue().splitlines()
        if "WARNING" in line
    ]


def test_an_undeclared_date_is_the_published_commits_date(
    committed_technote: Any, make_app: Any
) -> None:
    """A technote that declares no ``date_updated`` is cited by the date of
    the commit it was built from.

    That commit is the publication event: Rubin's technote CI publishes what
    it checks out, so the date the reader is invited to copy into a
    bibliography is the date the text they are reading was published. The
    BibTeX ``month`` is the same date's month, so the entry and the displayed
    citation cannot disagree.
    """
    srcdir = committed_technote("undated")

    doc = _build(make_app("html", srcdir=srcdir))

    (text,) = doc.cssselect(TEXT)
    (entry,) = doc.cssselect(BIBTEX_ENTRY)
    assert f"({COMMIT_YEAR})." in _text(text)
    assert f"year = {{{COMMIT_YEAR}}}," in entry.text_content()
    assert f"month = {{{COMMIT_MONTH}}}," in entry.text_content()


def test_the_citation_does_not_move_with_the_build_clock(
    committed_technote: Any, make_app: Any, evict_config_modules: Any
) -> None:
    """Rebuilding the same commit composes the same citation, because neither
    build reads the clock it ran under.

    The year of the build is the value that used to get in: ``technote``
    stamped it into the metadata's ``date_updated`` whenever technote.toml
    omitted the field, so a technote published years ago was cited to the
    current year and re-dated on every rebuild. Asserting that the year the
    build ran in appears nowhere in the entry is what pins that down; the two
    builds agreeing is what the reader of a stored BibTeX entry gets from it.
    """
    srcdir = committed_technote("rebuilt")
    doc = _build(make_app("html", srcdir=srcdir))
    (entry,) = doc.cssselect(BIBTEX_ENTRY)
    citation = entry.text_content()

    # Touch the document so the second build re-renders it. Sphinx writes
    # nothing for a page it finds up to date, and a page it did not write
    # would carry the first build's citation whatever the second composed.
    (srcdir / "index.rst").touch()
    evict_config_modules()
    second = make_app("html", srcdir=srcdir)
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


def test_a_declared_date_updated_wins_over_the_commit(
    committed_technote: Any, make_app: Any
) -> None:
    """A technote that declares ``date_updated`` is cited by that date, not
    by the commit it was built from.

    Declaring the field is how an author pins the citation to a fixed date —
    the day the work was published, rather than the day its last typo fix was
    committed — so the declared value has to beat a commit date that is
    otherwise perfectly good.
    """
    srcdir = committed_technote("declared", declared_date=DECLARED_DATE)

    doc = _build(make_app("html", srcdir=srcdir))

    (text,) = doc.cssselect(TEXT)
    (entry,) = doc.cssselect(BIBTEX_ENTRY)
    assert f"({DECLARED_YEAR})." in _text(text)
    assert f"year = {{{DECLARED_YEAR}}}," in entry.text_content()


def test_no_technote_reports_an_undated_citation(
    committed_technote: Any, make_app: Any
) -> None:
    """A technote build emits no ``documenteer.citation_date`` warning and
    does not load the extension that emits it.

    Every technote now carries a date, so the report has nothing left to say
    about one. Leaving the extension loaded would leave a ``-W`` technote one
    configuration change away from failing on a citation that is dated.
    """
    srcdir = committed_technote("unreported")

    app = make_app("html", srcdir=srcdir)
    app.build()

    assert "documenteer.ext.citationdate" not in app.extensions
    assert [line for line in _warnings(app) if WARNING_NAME in line] == []
