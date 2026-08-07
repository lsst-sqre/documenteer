"""Smoke tests for the documenteer command-line interface."""

from __future__ import annotations

from pathlib import Path

import pytest_responses  # noqa: F401
from click.testing import CliRunner
from responses import RequestsMock

from documenteer.cli import main

AUTHOR_JSON = """
{
    "affiliations": [],
    "family_name": "Sick",
    "given_name": "Jonathan",
    "internal_id": "sickj",
    "notes": [],
    "orcid": "https://orcid.org/0000-0003-3001-676X"
}
"""

VALID_TOML = """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "Jonathan"
name.family = "Sick"
internal_id = "sickj"
"""

MISSING_ID_TOML = """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "Jonathan"
name.family = "Sick"
"""


def test_lint_success(tmp_path: Path, responses: RequestsMock) -> None:
    """A valid technote with a resolvable author and abstract exits 0."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/sickj",
        body=AUTHOR_JSON,
        content_type="application/json",
        status=200,
    )
    (tmp_path / "technote.toml").write_text(VALID_TOML)
    (tmp_path / "index.rst").write_text(
        "#####\nTitle\n#####\n\n.. abstract::\n\n   An abstract.\n"
    )
    (tmp_path / "requirements.txt").write_text("documenteer[technote]\n")

    runner = CliRunner()
    result = runner.invoke(main, ["technote", "lint", "-d", str(tmp_path)])
    assert result.exit_code == 0, result.output


def test_lint_requirements_drift_strict(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """Requirements drift warns (exit 0) but is fatal under --strict."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/sickj",
        body=AUTHOR_JSON,
        content_type="application/json",
        status=200,
    )
    (tmp_path / "technote.toml").write_text(VALID_TOML)
    (tmp_path / "index.rst").write_text(
        "#####\nTitle\n#####\n\n.. abstract::\n\n   An abstract.\n"
    )
    # documenteer[technote] absent and sphinx pinned separately.
    (tmp_path / "requirements.txt").write_text("sphinx==8.1.0\n")

    runner = CliRunner()
    result = runner.invoke(main, ["technote", "lint", "-d", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "[TN002]" in result.output
    assert "[TN003]" in result.output

    strict = runner.invoke(
        main, ["technote", "lint", "-d", str(tmp_path), "--strict"]
    )
    assert strict.exit_code == 1, strict.output
    assert "[TN002]" in strict.output
    assert "[TN003]" in strict.output


def test_lint_missing_internal_id(tmp_path: Path) -> None:
    """An author missing an internal_id exits 1 with a TN101 finding."""
    (tmp_path / "technote.toml").write_text(MISSING_ID_TOML)

    runner = CliRunner()
    result = runner.invoke(main, ["technote", "lint", "-d", str(tmp_path)])
    assert result.exit_code == 1
    assert "[TN101]" in result.output


def test_lint_missing_toml_reports_tn004(tmp_path: Path) -> None:
    """A directory with no technote.toml exits 1 with a TN004 finding."""
    runner = CliRunner()
    result = runner.invoke(main, ["technote", "lint", "-d", str(tmp_path)])
    assert result.exit_code == 1
    assert "[TN004]" in result.output
    # A coded finding, not a traceback from an uncaught exception.
    assert result.exception is None or isinstance(result.exception, SystemExit)


def test_lint_malformed_toml_reports_tn005(tmp_path: Path) -> None:
    """A syntactically broken technote.toml exits 1 with a TN005 finding."""
    (tmp_path / "technote.toml").write_text("[technote\nid = ")

    runner = CliRunner()
    result = runner.invoke(main, ["technote", "lint", "-d", str(tmp_path)])
    assert result.exit_code == 1
    assert "[TN005]" in result.output
    # A coded finding, not a traceback from an uncaught TOMLDecodeError.
    assert result.exception is None or isinstance(result.exception, SystemExit)


def test_lint_corrupt_notebook_reports_tn203(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A corrupt index.ipynb exits 1 with a TN203 finding, not a traceback."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/sickj",
        body=AUTHOR_JSON,
        content_type="application/json",
        status=200,
    )
    (tmp_path / "technote.toml").write_text(VALID_TOML)
    (tmp_path / "index.ipynb").write_text("{ not valid json")
    (tmp_path / "requirements.txt").write_text("documenteer[technote]\n")

    runner = CliRunner()
    result = runner.invoke(main, ["technote", "lint", "-d", str(tmp_path)])
    assert result.exit_code == 1
    assert "[TN203]" in result.output
    # A coded finding, not a traceback from an uncaught JSONDecodeError.
    assert result.exception is None or isinstance(result.exception, SystemExit)
