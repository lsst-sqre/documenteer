"""Test the TechnoteUpdateService class."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
import pytest_responses  # noqa: F401
import yaml
from responses import RequestsMock

from documenteer.services.technoteupdate import (
    TEMPLATE_CONF_PY_CONTENTS,
    TOOLING_TEMPLATES,
    TechnoteUpdateService,
    UpdateStatus,
)
from documenteer.storage.authordb import AuthorDb
from documenteer.storage.technotetoml import TechnoteTomlFile

AUTHOR_RESPONSE = """
{
    "affiliations": [
        {
            "address": {
                "city": "Ontario",
                "country": "Canada",
                "postal_code": null,
                "state": null,
                "street": "Penetanguishene"
            },
            "department": null,
            "internal_id": "JSickCodes",
            "name": "J.Sick Codes Inc.",
            "ror": null
        },
        {
            "address": {
                "city": "Tucson",
                "country": "USA",
                "postal_code": "85719",
                "state": "AZ",
                "street": "950 N. Cherry Ave."
            },
            "department": null,
            "internal_id": "RubinObs",
            "name": "Vera C. Rubin Observatory Project Office",
            "ror": "https://ror.org/048g3cy84"
        }
    ],
    "family_name": "Sick",
    "given_name": "Jonathan",
    "internal_id": "sickj",
    "notes": [],
    "orcid": "https://orcid.org/0000-0003-3001-676X"
}
"""

LEGACY_CONTENT = """
:tocdepth: 1

.. Please do not modify tocdepth.

.. sectnum::

Introduction
============

Hello

.. rubric:: References

.. bibliography:: local.bib lsstbib/books.bib
   :style: lsst_aa
"""


def migrate_legacy_technote(
    tmp_path: Path, responses: RequestsMock
) -> TechnoteUpdateService:
    """Set up a legacy technote in ``tmp_path`` and migrate it."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/sickj",
        body=AUTHOR_RESPONSE,
        content_type="application/json",
        status=200,
    )
    metadata = {
        "series": "SQR",
        "serial_number": "065",
        "doc_title": "Design of Noteburst",
        "description": "Hello world.",
        "github_url": "https://github.com/lsst-sqre/sqr-065",
    }
    (tmp_path / "metadata.yaml").write_text(yaml.dump(metadata))
    (tmp_path / "index.rst").write_text(LEGACY_CONTENT)

    author_db = AuthorDb()
    service = TechnoteUpdateService(tmp_path, author_db)
    service.convert_legacy(author_ids=["sickj"])
    return service


def test_migration(tmp_path: Path, responses: RequestsMock) -> None:
    """Test migrating a technote."""
    migrate_legacy_technote(tmp_path, responses)

    toml_path = tmp_path / "technote.toml"
    assert toml_path.exists()

    toml_file = TechnoteTomlFile.open(toml_path)
    assert cast("str", toml_file.technote_table["id"]) == "SQR-065"
    assert cast("str", toml_file.technote_table["series_id"]) == "SQR"
    assert toml_file.author_ids == ["sickj"]


def test_migration_writes_tooling(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A migrated technote can run every Documenteer command it is told to."""
    migrate_legacy_technote(tmp_path, responses)

    requirements = (tmp_path / "requirements.txt").read_text()
    assert requirements.strip() == "documenteer[technote]>=2.5.0,<3"

    tox_ini = (tmp_path / "tox.ini").read_text()
    assert "[testenv:sync-authors]" in tox_ini
    assert "documenteer technote sync-authors" in tox_ini
    assert "[testenv:sync-cff]" in tox_ini
    assert "documenteer technote sync-cff" in tox_ini
    assert "[testenv:technote-lint]" in tox_ini
    assert "documenteer technote lint" in tox_ini

    makefile = (tmp_path / "Makefile").read_text()
    assert "sync-authors:\n\ttox run -e sync-authors" in makefile
    assert "sync-cff:\n\ttox run -e sync-cff" in makefile
    assert "tox run -e lint,technote-lint,linkcheck" in makefile


def test_migration_lint_env_checks_citation_file(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """The lint env enforces CITATION.cff freshness, not just the linter."""
    migrate_legacy_technote(tmp_path, responses)

    tox_ini = (tmp_path / "tox.ini").read_text()
    lint_env = tox_ini.split("[testenv:technote-lint]", 1)[1].split(
        "\n[testenv:", 1
    )[0]
    assert "documenteer technote lint" in lint_env
    assert "documenteer technote sync-cff --check" in lint_env


MODERN_TOML = """
[technote]
id = "SQR-065"
series_id = "SQR"
canonical_url = "https://sqr-065.lsst.io/"
github_url = "https://github.com/lsst-sqre/sqr-065"
"""

STALE_TOX_INI = """[tox]
environments = html
isolated_build = True

[testenv:html]
commands =
   sphinx-build -b html . _build/html
"""

CUSTOM_CONF_PY = """from documenteer.conf.technote import *  # noqa: F403

nitpick_ignore = [("py:class", "Thing")]
"""

README = "A README the update must not touch.\n"

INDEX_RST = "######\nSQR-65\n######\n"


def make_modern_technote(tmp_path: Path) -> None:
    """Set up a modern technote whose tooling is out of date."""
    (tmp_path / "technote.toml").write_text(MODERN_TOML)
    (tmp_path / "index.rst").write_text(INDEX_RST)
    (tmp_path / "README.rst").write_text(README)
    (tmp_path / "conf.py").write_text(CUSTOM_CONF_PY)
    (tmp_path / "tox.ini").write_text(STALE_TOX_INI)


def test_refresh_tooling_rewrites_stale_tox_ini(tmp_path: Path) -> None:
    """A modern technote's stale tox.ini is rewritten from the template."""
    make_modern_technote(tmp_path)

    service = TechnoteUpdateService(tmp_path, AuthorDb())
    service.refresh_tooling()

    tox_ini = (tmp_path / "tox.ini").read_text()
    assert "[testenv:sync-cff]" in tox_ini


def test_refresh_tooling_writes_every_standard_file(tmp_path: Path) -> None:
    """Every standard tooling file is present after an update."""
    make_modern_technote(tmp_path)

    service = TechnoteUpdateService(tmp_path, AuthorDb())
    service.refresh_tooling()

    for rel_path in TOOLING_TEMPLATES:
        assert (tmp_path / rel_path).is_file(), rel_path


def test_refresh_tooling_reports_each_file(tmp_path: Path) -> None:
    """Each standard file is reported, whether or not it changed."""
    make_modern_technote(tmp_path)

    service = TechnoteUpdateService(tmp_path, AuthorDb())
    outcomes = service.refresh_tooling()

    assert [outcome.path for outcome in outcomes] == [
        *TOOLING_TEMPLATES,
        "conf.py",
    ]
    assert all(
        outcome.status is UpdateStatus.updated
        for outcome in outcomes
        if outcome.path != "conf.py"
    )


def test_refresh_tooling_leaves_the_technotes_own_writing(
    tmp_path: Path,
) -> None:
    """The content file and README are the technote's, not the template's."""
    make_modern_technote(tmp_path)

    service = TechnoteUpdateService(tmp_path, AuthorDb())
    service.refresh_tooling()

    assert (tmp_path / "README.rst").read_text() == README
    assert (tmp_path / "index.rst").read_text() == INDEX_RST


def test_refresh_tooling_leaves_a_customized_conf_py(tmp_path: Path) -> None:
    """A conf.py with configuration of its own is reported, not rewritten."""
    make_modern_technote(tmp_path)

    service = TechnoteUpdateService(tmp_path, AuthorDb())
    outcomes = service.refresh_tooling()

    assert (tmp_path / "conf.py").read_text() == CUSTOM_CONF_PY
    conf_py = next(o for o in outcomes if o.path == "conf.py")
    assert conf_py.status is UpdateStatus.differs


def test_refresh_tooling_rewrites_a_template_conf_py(tmp_path: Path) -> None:
    """A conf.py Documenteer itself generated is brought up to date."""
    make_modern_technote(tmp_path)
    (tmp_path / "conf.py").write_text(
        "from documenteer.conf.technote import *  # noqa F401 F403\n"
    )

    service = TechnoteUpdateService(tmp_path, AuthorDb())
    outcomes = service.refresh_tooling()

    conf_py = next(o for o in outcomes if o.path == "conf.py")
    assert conf_py.status is UpdateStatus.updated
    assert (tmp_path / "conf.py").read_text() in TEMPLATE_CONF_PY_CONTENTS


def test_refresh_tooling_is_idempotent(tmp_path: Path) -> None:
    """A second update finds nothing left to do."""
    make_modern_technote(tmp_path)

    service = TechnoteUpdateService(tmp_path, AuthorDb())
    service.refresh_tooling()
    outcomes = service.refresh_tooling()

    assert all(
        outcome.status is UpdateStatus.unchanged
        for outcome in outcomes
        if outcome.path != "conf.py"
    )
    assert not any(outcome.changed for outcome in outcomes)


def test_refresh_tooling_skips_an_ignored_file(tmp_path: Path) -> None:
    """A file named by ignore_files is left exactly as the technote has it."""
    make_modern_technote(tmp_path)

    service = TechnoteUpdateService(tmp_path, AuthorDb())
    outcomes = service.refresh_tooling(ignore_files=["tox.ini"])

    assert (tmp_path / "tox.ini").read_text() == STALE_TOX_INI
    tox_ini = next(o for o in outcomes if o.path == "tox.ini")
    assert tox_ini.status is UpdateStatus.skipped


def test_refresh_tooling_dry_run_writes_nothing(tmp_path: Path) -> None:
    """A dry run reports the same drift it declines to fix."""
    make_modern_technote(tmp_path)

    service = TechnoteUpdateService(tmp_path, AuthorDb())
    outcomes = service.refresh_tooling(dry_run=True)

    assert (tmp_path / "tox.ini").read_text() == STALE_TOX_INI
    assert not (tmp_path / "Makefile").exists()
    assert any(outcome.changed for outcome in outcomes)


def test_refresh_tooling_context_comes_from_technote_toml(
    tmp_path: Path,
) -> None:
    """The CI workflow's handle is the one technote.toml declares."""
    make_modern_technote(tmp_path)

    service = TechnoteUpdateService(tmp_path, AuthorDb())
    service.refresh_tooling()

    ci_yaml = (tmp_path / ".github/workflows/ci.yaml").read_text()
    assert "handle: sqr-065" in ci_yaml


def test_refresh_tooling_needs_a_handle(tmp_path: Path) -> None:
    """A technote.toml with no handle cannot be updated."""
    (tmp_path / "technote.toml").write_text("[technote]\n")

    service = TechnoteUpdateService(tmp_path, AuthorDb())
    with pytest.raises(ValueError, match="handle"):
        service.refresh_tooling()


def test_is_legacy_distinguishes_the_two_formats(tmp_path: Path) -> None:
    """A technote.toml means a technote is not converted a second time."""
    service = TechnoteUpdateService(tmp_path, AuthorDb())
    empty = service.is_legacy

    (tmp_path / "metadata.yaml").write_text("series: SQR\n")
    legacy = service.is_legacy

    (tmp_path / "technote.toml").write_text(MODERN_TOML)
    converted = service.is_legacy

    assert (empty, legacy, converted) == (False, True, False)
