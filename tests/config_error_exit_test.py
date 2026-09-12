# type: ignore
"""Tests for how an invalid configuration file ends a Sphinx build.

A ``documenteer.toml`` or ``technote.toml`` that does not validate is a
mistake in a file a documentation author wrote, and the message the build
prints — Documenteer's own for a ``documenteer.toml``, the technote package's
for a ``technote.toml`` — says what is wrong with it. Sphinx renders every
`SphinxError`
raised while :file:`conf.py` runs inside a crash frame — a "Configuration
error!" banner, a versions dump, an abridged traceback, a saved-traceback
path, and an invitation to report the problem to sphinx-doc — which buries
that message in a report about Sphinx.

These builds run in subprocesses because the behavior under test *is* the
process exit: the preset terminates the interpreter rather than raising, so
there is nothing an in-process build could observe. Each is run both with and
without ``-T``, since ``-T`` is exactly the flag that asks Sphinx for the
traceback these builds must not print.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SPHINX_ISSUE_TRACKER = "sphinx-doc/sphinx/issues"
"""The invitation Sphinx's crash frame ends with.

Its presence in a build's output means the author was asked to report their
own typo to Sphinx's maintainers.
"""

INDEX_RST = """
##############
Example title
##############

Body text.
"""


def _write_guide(root: Path, toml: str) -> Path:
    """Write the smallest user guide that reads a ``documenteer.toml``."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "conf.py").write_text("from documenteer.conf.guide import *\n")
    (root / "index.rst").write_text(INDEX_RST)
    (root / "documenteer.toml").write_text(toml)
    return root


def _write_technote(root: Path, toml: str) -> Path:
    """Write the smallest technote that reads a ``technote.toml``."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "conf.py").write_text(
        "from documenteer.conf.technote import *\n"
        "documenteer_bibfile_github_repos: list = []\n"
    )
    (root / "index.rst").write_text(INDEX_RST)
    (root / "technote.toml").write_text(toml)
    return root


def _build(root: Path, *, show_traceback: bool) -> tuple[int, str]:
    """Build a project in a subprocess, returning its exit code and output."""
    argv = [sys.executable, "-m", "sphinx", "-b", "html", ".", "_build"]
    if show_traceback:
        argv.append("-T")
    result = subprocess.run(
        argv, cwd=root, capture_output=True, text=True, check=False
    )
    return result.returncode, result.stdout + result.stderr


def _assert_reported_once(output: str, sentence: str) -> None:
    """Assert that the build said one thing, once, and said nothing of
    Sphinx's own crash reporting.
    """
    assert output.count(sentence) == 1, output
    assert "Traceback" not in output, output
    assert SPHINX_ISSUE_TRACKER not in output, output


GUIDE_BAD_DATE = """
[project]
title = "Example Guide"
base_url = "https://example.lsst.io"
github_url = "https://github.com/lsst-sqre/example"

[[project.citations]]
doi = "10.71929/rubin/3382539"
self = true
title = "Example Guide"
date = "not-a-date"
"""


@pytest.mark.parametrize("show_traceback", [False, True])
def test_guide_reports_a_bad_date_without_a_crash_frame(
    tmp_path: Path, *, show_traceback: bool
) -> None:
    """A guide whose citation date is not a date fails with Documenteer's
    sentence about the date and nothing else.
    """
    root = _write_guide(tmp_path / "guide", GUIDE_BAD_DATE)

    returncode, output = _build(root, show_traceback=show_traceback)

    assert returncode != 0
    _assert_reported_once(
        output, "The citation date 'not-a-date' is not a date."
    )
    assert "[[project.citations]] entry #1, field date" in output


TECHNOTE_BAD_DOI = """
[technote]
id = "SQR-000"
series_id = "SQR"
canonical_url = "https://sqr-000.lsst.io/"
github_url = "https://github.com/lsst-sqre/sqr-000"
doi = "10.71929"
"""


@pytest.mark.parametrize("show_traceback", [False, True])
def test_technote_reports_a_bad_doi_without_a_crash_frame(
    tmp_path: Path, *, show_traceback: bool
) -> None:
    """A technote whose ``doi`` is not a DOI names the field and the form a
    DOI is written in.

    Older technote releases raised a `~sphinx.errors.ConfigError` saying only
    that there was a "syntax or validation issue" somewhere in the file.
    Naming the field is the whole point of the message that replaced it, so
    the absence of that sentence is asserted alongside the field.
    """
    root = _write_technote(tmp_path / "technote", TECHNOTE_BAD_DOI)

    returncode, output = _build(root, show_traceback=show_traceback)

    assert returncode != 0
    _assert_reported_once(output, "Not a DOI (10.71929).")
    assert "[technote] doi" in output
    assert "10.5281/zenodo.10385500" in output
    assert "Syntax or validation issue" not in output


TECHNOTE_LOWERCASE_LINT_CODE = """
[technote]
id = "SQR-000"
series_id = "SQR"
canonical_url = "https://sqr-000.lsst.io/"
github_url = "https://github.com/lsst-sqre/sqr-000"

[technote.lint]
ignore = ["tn105"]
"""


@pytest.mark.parametrize("show_traceback", [False, True])
def test_technote_reports_a_lowercase_lint_code(
    tmp_path: Path, *, show_traceback: bool
) -> None:
    """A lint rule code written in lowercase names the table it is in and the
    shape a rule code has.
    """
    root = _write_technote(tmp_path / "technote", TECHNOTE_LOWERCASE_LINT_CODE)

    returncode, output = _build(root, show_traceback=show_traceback)

    assert returncode != 0
    _assert_reported_once(output, "Not a lint rule code ('tn105').")
    assert "[technote.lint] ignore" in output
    assert "TN105" in output


TECHNOTE_BAD_AFFILIATION_ROR = """
[technote]
id = "SQR-000"
series_id = "SQR"
canonical_url = "https://sqr-000.lsst.io/"
github_url = "https://github.com/lsst-sqre/sqr-000"

[[technote.authors]]
name = {given = "Jane", family = "Doe"}

[[technote.authors.affiliations]]
name = "Rubin Observatory"
ror = "not-a-ror"
"""


@pytest.mark.parametrize("show_traceback", [False, True])
def test_technote_reports_a_malformed_affiliation_ror(
    tmp_path: Path, *, show_traceback: bool
) -> None:
    """An affiliation whose ``ror`` is not a URL is addressed by the word
    technote calls one item of that array, not by a word of Documenteer's.

    An error nested two arrays deep is where the two formatters could
    disagree: only the technote package knows that one item of
    ``affiliations`` is an affiliation, so relaying its message verbatim is
    what puts that word in front of the author.
    """
    root = _write_technote(tmp_path / "technote", TECHNOTE_BAD_AFFILIATION_ROR)

    returncode, output = _build(root, show_traceback=show_traceback)

    assert returncode != 0
    _assert_reported_once(
        output, "[[technote.authors]] author #1, affiliation #1, field ror"
    )
    assert "Syntax or validation issue" not in output


READ_PROBE = """
import sys
from pathlib import Path

from documenteer.services.technoteread import TechnoteReadError, read_technote

try:
    read_technote(Path(sys.argv[1]))
except TechnoteReadError as error:
    sys.stdout.write(f"RAISED: {error}\\n")
else:
    sys.stdout.write("READ\\n")
"""
"""Read a technote the way ``documenteer technote sync-cff`` does, and report
whether the read raised rather than ending the process.

Run as a subprocess because the failure it guards against is a process exit:
an in-process check would take the test session down with it and say nothing
about which behavior broke.
"""


def test_a_read_technote_raises_instead_of_exiting(tmp_path: Path) -> None:
    """A build Documenteer drives in its own process reports an invalid
    technote.toml by raising, not by exiting.

    ``documenteer technote sync-cff`` and ``technote lint`` read a technote by
    running its Sphinx build in the command's own process, which imports the
    same preset ``sphinx-build`` does. Exiting there would take the command
    down mid-run, with its own report — the lint findings, the CFF diff —
    never printed.
    """
    root = _write_technote(tmp_path / "technote", TECHNOTE_BAD_DOI)

    result = subprocess.run(
        [sys.executable, "-c", READ_PROBE, str(root)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("RAISED:")
    assert "Not a DOI (10.71929)." in result.stdout
