"""Smoke tests for the documenteer command-line interface."""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

import pytest
import pytest_responses  # noqa: F401
import requests
import yaml
from click.testing import CliRunner
from responses import RequestsMock, matchers

from documenteer.cli import main
from documenteer.services.technotelint import CHECKS

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
    # The footer links each fired rule to its documentation landing page.
    assert (
        "TN101: https://documenteer.lsst.io/technotes/lint/tn101.html"
        in result.output
    )


def test_lint_ignore_option_silences_a_rule(tmp_path: Path) -> None:
    """--ignore turns a rule off and says so in the summary."""
    (tmp_path / "technote.toml").write_text(MISSING_ID_TOML)

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["technote", "lint", "-d", str(tmp_path), "--ignore", "TN101"],
    )
    assert result.exit_code == 0, result.output
    assert "[TN101]" not in result.output
    assert "Ignored 1 rule: TN101 (--ignore)." in result.output


def test_lint_file_ignore_names_its_source(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A rule ignored by technote.toml is reported as off, not as passing."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/sickj",
        body=AUTHOR_JSON,
        content_type="application/json",
        status=200,
    )
    (tmp_path / "technote.toml").write_text(
        VALID_TOML + '\n[technote.lint]\nignore = ["TN002", "TN003"]\n'
    )
    (tmp_path / "index.rst").write_text(
        "#####\nTitle\n#####\n\n.. abstract::\n\n   An abstract.\n"
    )
    # documenteer[technote] absent and sphinx pinned separately: TN002/TN003.
    (tmp_path / "requirements.txt").write_text("sphinx==8.1.0\n")

    runner = CliRunner()
    result = runner.invoke(main, ["technote", "lint", "-d", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "[TN002]" not in result.output
    assert (
        "Ignored 2 rules: TN002 (technote.toml [technote.lint]), "
        "TN003 (technote.toml [technote.lint])." in result.output
    )
    # --strict has nothing left to promote, so the run stays green.
    strict = runner.invoke(
        main, ["technote", "lint", "-d", str(tmp_path), "--strict"]
    )
    assert strict.exit_code == 0, strict.output


def test_lint_unknown_ignore_code_reports_tn007(tmp_path: Path) -> None:
    """A --ignore typo is a TN007 finding, not a silently ignored option."""
    (tmp_path / "technote.toml").write_text(MISSING_ID_TOML)

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["technote", "lint", "-d", str(tmp_path), "--ignore", "TN150"],
    )
    assert result.exit_code == 1, result.output
    assert "[TN007]" in result.output
    assert "[TN101]" in result.output


def test_lint_footer_links_come_from_the_check_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The "Learn more" footer links where the rule says it is documented.

    Every rule in the registry documents itself on documenteer.lsst.io today,
    so this is the only way to see that the footer reads `Check.docs_url`
    rather than deriving a Documenteer URL from the code.
    """
    monkeypatch.setitem(
        CHECKS,
        "TN101",
        replace(CHECKS["TN101"], docs_url="https://example.org/tn101.html"),
    )
    (tmp_path / "technote.toml").write_text(MISSING_ID_TOML)

    runner = CliRunner()
    result = runner.invoke(main, ["technote", "lint", "-d", str(tmp_path)])
    assert result.exit_code == 1
    assert "TN101: https://example.org/tn101.html" in result.output


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


def test_add_author_unreachable_db(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """An unreachable author database exits 1 with a message, not a trace."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/sickj",
        body=requests.ConnectionError("connection refused"),
    )
    toml_path = tmp_path / "technote.toml"
    toml_path.write_text(MISSING_ID_TOML)

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["technote", "add-author", "-a", "sickj", "-t", str(toml_path)],
    )
    assert result.exit_code == 1
    assert "Failed to fetch author sickj" in result.output
    # A reported error, not a traceback from an uncaught transport failure.
    assert result.exception is None or isinstance(result.exception, SystemExit)
    # The file is left exactly as it was found.
    assert toml_path.read_text() == MISSING_ID_TOML


def test_add_author_malformed_id_record(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A 200 that is not an author record exits 1 plainly, not with a trace."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/sickj",
        body='{"not": "an author"}',
        content_type="application/json",
        status=200,
    )
    toml_path = tmp_path / "technote.toml"
    toml_path.write_text(MISSING_ID_TOML)

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["technote", "add-author", "-a", "sickj", "-t", str(toml_path)],
    )
    assert result.exit_code == 1
    assert (
        "The Rubin author database returned a malformed record for "
        "internal_id 'sickj'." in result.output
    )
    # A reported error, not a traceback from an uncaught ValidationError, and
    # not pydantic's field-by-field dump either.
    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert "validation error" not in result.output
    # The file is left exactly as it was found.
    assert toml_path.read_text() == MISSING_ID_TOML


def test_add_author_malformed_orcid_record(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A malformed ORCID-lookup body exits 1 plainly, not with a traceback."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors",
        body='{"not": "a listing"}',
        content_type="application/json",
        status=200,
        match=[matchers.query_param_matcher({"orcid": "0000-0003-3001-676X"})],
    )
    toml_path = tmp_path / "technote.toml"
    toml_path.write_text(MISSING_ID_TOML)

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "technote",
            "add-author",
            "--orcid",
            "0000-0003-3001-676X",
            "-t",
            str(toml_path),
        ],
    )
    assert result.exit_code == 1
    assert (
        "The Rubin author database returned a malformed record for "
        "ORCID 0000-0003-3001-676X." in result.output
    )
    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert "validation error" not in result.output
    assert toml_path.read_text() == MISSING_ID_TOML


CFF_TOML = """
[technote]
id = "SQR-000"
title = "The LSST DM Technical Note Publishing Platform"
canonical_url = "https://sqr-000.lsst.io/"
doi = "10.71929/rubin/2570308"
date_updated = 2026-08-24

[technote.organization]
name = "Vera C. Rubin Observatory"

[[technote.authors]]
name = {given = "Jonathan", family = "Sick"}
internal_id = "sickj"
orcid = "https://orcid.org/0000-0003-3001-676X"
"""


def test_sync_cff_writes_and_is_idempotent(tmp_path: Path) -> None:
    """sync-cff writes CITATION.cff, and a second run changes nothing."""
    (tmp_path / "technote.toml").write_text(CFF_TOML)
    runner = CliRunner()

    result = runner.invoke(main, ["technote", "sync-cff", "-d", str(tmp_path)])
    assert result.exit_code == 0, result.output
    cff_path = tmp_path / "CITATION.cff"
    written = cff_path.read_bytes()
    assert b"preferred-citation" in written

    result = runner.invoke(main, ["technote", "sync-cff", "-d", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert cff_path.read_bytes() == written


def test_sync_cff_warns_once_about_a_missing_date(tmp_path: Path) -> None:
    """A technote dated only by its creation still generates a file, and the
    command says once why that file carries no release date.
    """
    (tmp_path / "technote.toml").write_text(
        CFF_TOML.replace(
            "date_updated = 2026-08-24", "date_created = 2016-05-02T20:47:13Z"
        )
    )
    runner = CliRunner()

    result = runner.invoke(main, ["technote", "sync-cff", "-d", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert result.output.count("declares no date_updated") == 1
    assert "date-released" not in (tmp_path / "CITATION.cff").read_text()


def test_sync_cff_check_absent(tmp_path: Path) -> None:
    """--check passes when no CITATION.cff exists: adoption is opt-in."""
    (tmp_path / "technote.toml").write_text(CFF_TOML)

    runner = CliRunner()
    result = runner.invoke(
        main, ["technote", "sync-cff", "-d", str(tmp_path), "--check"]
    )

    assert result.exit_code == 0, result.output
    assert not (tmp_path / "CITATION.cff").exists()


def test_sync_cff_check_stale(tmp_path: Path) -> None:
    """--check fails on a stale CITATION.cff, and does not rewrite it."""
    (tmp_path / "technote.toml").write_text(CFF_TOML)
    cff_path = tmp_path / "CITATION.cff"
    cff_path.write_text("cff-version: 1.2.0\n")

    runner = CliRunner()
    result = runner.invoke(
        main, ["technote", "sync-cff", "-d", str(tmp_path), "--check"]
    )

    assert result.exit_code == 1
    assert cff_path.read_text() == "cff-version: 1.2.0\n"


def test_sync_cff_check_current(tmp_path: Path) -> None:
    """--check passes once CITATION.cff has been synced."""
    (tmp_path / "technote.toml").write_text(CFF_TOML)
    runner = CliRunner()
    runner.invoke(main, ["technote", "sync-cff", "-d", str(tmp_path)])

    result = runner.invoke(
        main, ["technote", "sync-cff", "-d", str(tmp_path), "--check"]
    )

    assert result.exit_code == 0, result.output


def test_sync_cff_without_technote_toml(tmp_path: Path) -> None:
    """A directory that is not a technote is reported, not tracebacked."""
    runner = CliRunner()
    result = runner.invoke(main, ["technote", "sync-cff", "-d", str(tmp_path)])

    assert result.exit_code == 1
    assert "technote.toml" in result.output


def test_sync_cff_malformed_doi(tmp_path: Path) -> None:
    """A DOI that is not a DOI is reported as a user error."""
    (tmp_path / "technote.toml").write_text(
        CFF_TOML.replace('doi = "10.71929/rubin/2570308"', 'doi = "nope"')
    )

    runner = CliRunner()
    result = runner.invoke(main, ["technote", "sync-cff", "-d", str(tmp_path)])

    assert result.exit_code == 1
    assert "Not a DOI" in result.output


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        pytest.param(
            CFF_TOML.replace(
                'name = {given = "Jonathan", family = "Sick"}',
                'name = "Jonathan Sick"',
            ),
            "The name of [[technote.authors]] entry 1",
            id="name",
        ),
        pytest.param(
            CFF_TOML + 'affiliations = ["Rubin Observatory"]\n',
            "Affiliation 1 of [[technote.authors]] entry 1",
            id="affiliation",
        ),
    ],
)
def test_sync_cff_malformed_author_shape(
    tmp_path: Path, source: str, expected: str
) -> None:
    """An author field written as the wrong TOML type is reported as a user
    error, not raised as a traceback out of the pre-commit hook.
    """
    (tmp_path / "technote.toml").write_text(source)

    runner = CliRunner()
    result = runner.invoke(main, ["technote", "sync-cff", "-d", str(tmp_path)])

    assert result.exit_code == 1
    assert expected in result.output
    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert not (tmp_path / "CITATION.cff").exists()


def test_precommit_hook_definition() -> None:
    """The repository ships a technote-sync-cff pre-commit hook."""
    hooks_path = Path(__file__).parent.parent / ".pre-commit-hooks.yaml"
    hooks = yaml.safe_load(hooks_path.read_text())

    hook = next(h for h in hooks if h["id"] == "technote-sync-cff")
    assert hook["entry"] == "documenteer technote sync-cff"
    assert hook["pass_filenames"] is False
    assert re.match(hook["files"], "technote.toml")
