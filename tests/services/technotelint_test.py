"""Tests for the TechnoteLintService class."""

from __future__ import annotations

import json
from pathlib import Path

import pytest_responses  # noqa: F401
import requests
from responses import RequestsMock

from documenteer.services.technotelint import (
    LintContext,
    Severity,
    TechnoteLintService,
    check_abstract,
    check_requirements,
)
from documenteer.storage.authordb import AuthorDb

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


def _search_result(
    internal_id: str,
    given_name: str,
    family_name: str,
    score: float,
    orcid: str | None = None,
) -> dict[str, object]:
    """Build one entry of an Ook author-search response body."""
    return {
        "affiliations": [],
        "family_name": family_name,
        "given_name": given_name,
        "internal_id": internal_id,
        "notes": [],
        "orcid": orcid,
        "score": score,
    }


def _write_technote(tmp_path: Path, toml_content: str) -> LintContext:
    """Write a technote.toml into ``tmp_path`` and build a context.

    Also writes an ``index.rst`` with a well-formed abstract and a sane
    ``requirements.txt`` so the content-group abstract check (TN201/TN202)
    and the structural requirements check (TN002/TN003) stay silent and
    these metadata-focused tests observe only author/schema findings.
    """
    (tmp_path / "technote.toml").write_text(toml_content)
    (tmp_path / "index.rst").write_text(
        "#####\nTitle\n#####\n\n.. abstract::\n\n   An abstract.\n"
    )
    (tmp_path / "requirements.txt").write_text("documenteer[technote]\n")
    return LintContext.from_dir(tmp_path, AuthorDb())


def test_valid_authors_pass(tmp_path: Path, responses: RequestsMock) -> None:
    """A schema-valid technote with a resolvable author has no findings."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/sickj",
        body=AUTHOR_JSON,
        content_type="application/json",
        status=200,
    )
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "Jonathan"
name.family = "Sick"
internal_id = "sickj"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert findings == []


def test_missing_internal_id(tmp_path: Path) -> None:
    """Each author lacking an internal_id yields one TN101 error."""
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "Jonathan"
name.family = "Sick"

[[technote.authors]]
name.given = "Frossie"
name.family = "Economou"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN101", "TN101"]
    assert all(f.severity is Severity.error for f in findings)


def test_missing_internal_id_suggests_orcid_match(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A TN101 author whose ORCID is in the DB gets a suggested ID."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors",
        body=json.dumps(
            [
                _search_result(
                    "alsayyady",
                    "Yusra",
                    "AlSayyad",
                    90.0,
                    orcid="https://orcid.org/0009-0008-9216-7516",
                ),
                _search_result("aliee", "Eman E.", "Ali", 40.0),
            ]
        ),
        content_type="application/json",
        status=200,
    )
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "Yusra"
name.family = "AlSayyad"
orcid = "https://orcid.org/0009-0008-9216-7516"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN101"]
    assert findings[0].message == (
        "Author Yusra AlSayyad is missing an internal_id. Did you mean "
        "'alsayyady' (matched by ORCID)? Run 'documenteer technote "
        "sync-authors' after adding it."
    )


def test_internal_id_not_found(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """An internal_id absent from the author DB (404) yields TN102."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/nobody",
        body="Not found",
        status=404,
    )
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "No"
name.family = "Body"
internal_id = "nobody"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN102"]
    assert findings[0].severity is Severity.error


def test_unknown_internal_id_suggests_name_match(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A TN102 author with one near-exact name match gets a suggested ID."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/lynnej",
        body="Not found",
        status=404,
    )
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors",
        body=json.dumps(
            [
                _search_result("jonesrl", "R. Lynne", "Jones", 90.0),
                _search_result("jonesd", "Derek", "Jones", 70.0),
                _search_result("jonesrwl", "Roger", "Jones", 70.0),
            ]
        ),
        content_type="application/json",
        status=200,
    )
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "Lynne"
name.family = "Jones"
internal_id = "lynnej"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN102"]
    assert findings[0].message == (
        "Author Lynne Jones has internal_id 'lynnej', which is not in the "
        "author database. Did you mean 'jonesrl' (R. Lynne Jones, matched "
        "by name)?"
    )


def test_ambiguous_name_match_keeps_plain_message(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """Several equally-good name matches suggest nothing."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors",
        body=json.dumps(
            [
                _search_result("jonesd", "Derek", "Jones", 90.0),
                _search_result("jonesrl", "R. Lynne", "Jones", 90.0),
            ]
        ),
        content_type="application/json",
        status=200,
    )
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "L."
name.family = "Jones"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN101"]
    assert findings[0].message == "Author L. Jones is missing an internal_id."


def test_weak_name_match_keeps_plain_message(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A search with no near-exact result suggests nothing."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors",
        body=json.dumps([_search_result("jonesd", "Derek", "Jones", 45.0)]),
        content_type="application/json",
        status=200,
    )
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "Nemo"
name.family = "Nobody"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN101"]
    assert (
        findings[0].message == "Author Nemo Nobody is missing an internal_id."
    )


def test_conflicting_orcid_keeps_plain_message(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A name match whose ORCID differs is a different person, so no hint."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors",
        body=json.dumps(
            [
                _search_result(
                    "jonesd",
                    "Derek",
                    "Jones",
                    90.0,
                    orcid="https://orcid.org/0000-0001-5916-0031",
                )
            ]
        ),
        content_type="application/json",
        status=200,
    )
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "Derek"
name.family = "Jones"
orcid = "https://orcid.org/0000-0003-3001-676X"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN101"]
    assert (
        findings[0].message == "Author Derek Jones is missing an internal_id."
    )


def test_suggestion_lookup_failure_keeps_plain_message(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A failed suggestion lookup leaves the finding as it was."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors",
        body="Internal server error",
        status=500,
    )
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "Jonathan"
name.family = "Sick"
orcid = "https://orcid.org/0000-0003-3001-676X"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN101"]
    assert findings[0].severity is Severity.error
    assert (
        findings[0].message
        == "Author Jonathan Sick is missing an internal_id."
    )


def test_authordb_unreachable(tmp_path: Path, responses: RequestsMock) -> None:
    """An unreachable author DB yields a TN103 warning, not an error."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/sickj",
        body=requests.ConnectionError("connection refused"),
    )
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "Jonathan"
name.family = "Sick"
internal_id = "sickj"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN103"]
    assert findings[0].severity is Severity.warning


def test_invalid_schema_skips_author_checks(tmp_path: Path) -> None:
    """A schema failure yields TN001 and skips the model-dependent checks."""
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "Jonathan"

[[technote.authors]]
name.given = "Frossie"
name.family = "Economou"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    # The second author has no internal_id, but TN101 needs the parsed model,
    # so only the schema finding is reported.
    assert [f.code for f in findings] == ["TN001"]
    assert findings[0].severity is Severity.error


def test_invalid_schema_still_runs_toml_independent_checks(
    tmp_path: Path,
) -> None:
    """A schema failure no longer suppresses the TN002/TN2xx checks."""
    (tmp_path / "technote.toml").write_text(
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "Jonathan"
"""
    )
    (tmp_path / "index.rst").write_text(
        "#####\nTitle\n#####\n\nIntroduction\n============\n\nBody.\n"
    )
    (tmp_path / "requirements.txt").write_text("sphinx==8.1.0\n")
    context = LintContext.from_dir(tmp_path, AuthorDb())
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN001", "TN201", "TN002", "TN003"]


def test_legacy_single_string_author_name_reports_tn001(
    tmp_path: Path,
) -> None:
    """The removed ``name = {name = "..."}`` form gets a targeted message."""
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name = { name = "Jonathan Sick" }
internal_id = "sickj"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN001"]
    message = findings[0].message
    assert 'name = { name = "Full Name" }' in message
    assert "technote 0.5" in message
    assert 'name = { given = "Given", family = "Family" }' in message
    assert "documenteer technote migrate" in message
    # The pydantic detail is retained for anyone debugging the schema error.
    assert "technote.authors.0.name" in message


def test_legacy_split_name_keys_report_tn001(tmp_path: Path) -> None:
    """The renamed ``given_names``/``family_names`` keys are called out."""
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name = { given_names = "Jonathan", family_names = "Sick" }
internal_id = "sickj"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN001"]
    message = findings[0].message
    assert 'name = { given_names = "...", family_names = "..." }' in message
    assert "renamed in November 2023" in message
    assert 'name = { given = "Given", family = "Family" }' in message
    assert "documenteer technote migrate" in message


def test_non_author_schema_error_has_no_legacy_message(
    tmp_path: Path,
) -> None:
    """A schema error unrelated to author names keeps the plain message."""
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"
canonical_url = "not a url"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN001"]
    message = findings[0].message
    assert "documenteer technote migrate" not in message
    assert "canonical_url" in message


def test_other_author_schema_error_has_no_legacy_message(
    tmp_path: Path,
) -> None:
    """An author with a non-legacy schema error keeps the plain message."""
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name = { given = "Jonathan", family = "Sick" }
orcid = "not-an-orcid"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN001"]
    assert "documenteer technote migrate" not in findings[0].message


def test_missing_toml_reports_tn004(tmp_path: Path) -> None:
    """A directory with no technote.toml yields a single TN004 error."""
    context = LintContext.from_dir(tmp_path, AuthorDb())
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN004"]
    assert findings[0].severity is Severity.error


def test_malformed_toml_reports_tn005(tmp_path: Path) -> None:
    """A syntactically broken technote.toml yields a TN005 error.

    The TOML-independent checks still run, so the missing abstract and
    requirements.txt are reported in the same pass.
    """
    (tmp_path / "technote.toml").write_text("[technote\nid = ")
    (tmp_path / "index.rst").write_text(
        "#####\nTitle\n#####\n\nIntroduction\n============\n\nBody.\n"
    )
    context = LintContext.from_dir(tmp_path, AuthorDb())
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN005", "TN201", "TN002"]
    assert findings[0].severity is Severity.error


def test_author_record_malformed_reports_tn102(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A 200 response with an unparseable author body yields a TN102 error."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/sickj",
        body="{ not valid json",
        content_type="application/json",
        status=200,
    )
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "Jonathan"
name.family = "Sick"
internal_id = "sickj"
""",
    )
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN102"]
    assert findings[0].severity is Severity.error
    assert "malformed" in findings[0].message


def _write_non_sphinx_technote(tmp_path: Path, toml_content: str) -> None:
    """Write a non-Sphinx technote: a technote.toml, no index, no conf.py.

    Mirrors a technote-series repository that is published through the shared
    technote CI with a custom build command (for example an org-mode deck),
    including the deliberately empty ``requirements.txt`` such a repository
    carries.
    """
    (tmp_path / "technote.toml").write_text(toml_content)
    (tmp_path / "requirements.txt").write_text("")


def test_non_sphinx_technote_passes(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A healthy non-Sphinx technote reports nothing, so the run exits 0."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/sickj",
        body=AUTHOR_JSON,
        content_type="application/json",
        status=200,
    )
    _write_non_sphinx_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "Jonathan"
name.family = "Sick"
internal_id = "sickj"
""",
    )
    context = LintContext.from_dir(tmp_path, AuthorDb())
    service = TechnoteLintService(context)
    assert service.lint() == []


def test_non_sphinx_technote_reports_schema_errors(tmp_path: Path) -> None:
    """A non-Sphinx technote's technote.toml is still schema-checked."""
    _write_non_sphinx_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"
canonical_url = "not a url"
""",
    )
    context = LintContext.from_dir(tmp_path, AuthorDb())
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN001"]


def test_non_sphinx_technote_runs_author_checks(
    tmp_path: Path, responses: RequestsMock
) -> None:
    """A non-Sphinx technote's authors are still resolved against the DB."""
    responses.get(
        "https://roundtable.lsst.cloud/ook/authors/nobody",
        body="Not found",
        status=404,
    )
    _write_non_sphinx_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "No"
name.family = "Body"
internal_id = "nobody"
""",
    )
    context = LintContext.from_dir(tmp_path, AuthorDb())
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN102"]


def _context_with_content(
    tmp_path: Path, filename: str, content: str
) -> LintContext:
    """Write a minimal technote.toml plus a content file, build a context.

    Also writes a sane ``requirements.txt`` so the structural requirements
    check (TN002/TN003) stays silent for content-focused tests that route
    through the full ``lint()`` aggregation.
    """
    (tmp_path / "technote.toml").write_text('[technote]\nid = "SQR-000"\n')
    (tmp_path / filename).write_text(content)
    (tmp_path / "requirements.txt").write_text("documenteer[technote]\n")
    return LintContext.from_dir(tmp_path, AuthorDb())


def _ipynb(*markdown_sources: str) -> str:
    """Serialize markdown cell sources into ``.ipynb`` JSON text."""
    cells = [
        {"cell_type": "markdown", "metadata": {}, "source": source}
        for source in markdown_sources
    ]
    return json.dumps(
        {"cells": cells, "metadata": {}, "nbformat": 4, "nbformat_minor": 5}
    )


RST_WITH_ABSTRACT = """\
#############
Demo technote
#############

.. abstract::

   A technote is a web-native single page document.

Introduction
============

Body text.
"""

MD_WITH_ABSTRACT = """\
# Demo technote

```{abstract}
A technote is a web-native single page document.
```

## Introduction

Body text.
"""

MD_WITH_COLON_ABSTRACT = """\
# Demo technote

:::{abstract}
A technote is a web-native single page document.
:::

## Introduction

Body text.
"""


def test_abstract_directive_rst_passes(tmp_path: Path) -> None:
    """A non-empty ``.. abstract::`` directive in index.rst passes."""
    context = _context_with_content(tmp_path, "index.rst", RST_WITH_ABSTRACT)
    assert check_abstract(context) == []


def test_abstract_directive_md_passes(tmp_path: Path) -> None:
    """A non-empty ```` ```{abstract} ```` fence in index.md passes."""
    context = _context_with_content(tmp_path, "index.md", MD_WITH_ABSTRACT)
    assert check_abstract(context) == []


def test_abstract_colon_directive_md_passes(tmp_path: Path) -> None:
    """A non-empty ``:::{abstract}`` fence in index.md passes."""
    context = _context_with_content(
        tmp_path, "index.md", MD_WITH_COLON_ABSTRACT
    )
    assert check_abstract(context) == []


def test_abstract_directive_ipynb_passes(tmp_path: Path) -> None:
    """A non-empty abstract directive in an index.ipynb cell passes."""
    content = _ipynb(
        "# Demo technote\n"
        "\n"
        "```{abstract}\n"
        "A technote is a web-native single page document.\n"
        "```",
        "## Introduction\n\nBody text.",
    )
    context = _context_with_content(tmp_path, "index.ipynb", content)
    assert check_abstract(context) == []


def test_rst_abstract_body_on_marker_line_passes(tmp_path: Path) -> None:
    """``.. abstract:: text`` is valid rST: the text is directive content."""
    content = (
        "#############\nDemo technote\n#############\n\n"
        ".. abstract:: A technote is a web-native single page document.\n\n"
        "Introduction\n============\n\nBody text.\n"
    )
    context = _context_with_content(tmp_path, "index.rst", content)
    assert check_abstract(context) == []


def test_mixed_case_rst_abstract_directive_passes(tmp_path: Path) -> None:
    """Docutils lowercases directive names, so ``.. Abstract::`` builds."""
    content = (
        "#############\nDemo technote\n#############\n\n"
        ".. Abstract::\n\n"
        "   A technote is a web-native single page document.\n\n"
        "Introduction\n============\n\nBody text.\n"
    )
    context = _context_with_content(tmp_path, "index.rst", content)
    assert check_abstract(context) == []


def test_mixed_case_myst_abstract_directive_passes(tmp_path: Path) -> None:
    """Docutils lowercases directive names, so ```{Abstract} builds."""
    content = (
        "# Demo technote\n\n"
        "```{Abstract}\n"
        "A technote is a web-native single page document.\n"
        "```\n\n"
        "## Introduction\n\nBody text.\n"
    )
    context = _context_with_content(tmp_path, "index.md", content)
    assert check_abstract(context) == []


def test_empty_myst_abstract_directive_reports_tn204(tmp_path: Path) -> None:
    """A MyST abstract fence with no body is reported with its location."""
    content = "# Demo technote\n\n```{abstract}\n```\n\n## Introduction\n"
    context = _context_with_content(tmp_path, "index.md", content)
    findings = check_abstract(context)
    assert [f.code for f in findings] == ["TN204"]
    assert findings[0].message.startswith("index.md:3:")
    # MyST content is pointed at the fenced directive, not the rST form.
    assert "```{abstract}" in findings[0].message
    assert ".. abstract::" not in findings[0].message


def test_unindented_rst_abstract_body_reports_tn204(tmp_path: Path) -> None:
    """An ``.. abstract::`` whose body is at column 0 is an empty directive."""
    content = """\
#############
Demo technote
#############

.. abstract::

A technote is a web-native single page document.

Introduction
============

Body text.
"""
    context = _context_with_content(tmp_path, "index.rst", content)
    findings = check_abstract(context)
    assert [f.code for f in findings] == ["TN204"]
    assert findings[0].severity is Severity.error
    assert findings[0].message.startswith("index.rst:5:")
    assert ".. abstract::" in findings[0].message


def test_no_abstract_reports_tn201(tmp_path: Path) -> None:
    """Content with neither a directive nor a heading yields TN201."""
    content = """\
#############
Demo technote
#############

Introduction
============

Body text.
"""
    context = _context_with_content(tmp_path, "index.rst", content)
    findings = check_abstract(context)
    assert [f.code for f in findings] == ["TN201"]
    assert findings[0].severity is Severity.error


def test_missing_content_file_yields_no_abstract_finding(
    tmp_path: Path,
) -> None:
    """A missing index file is TN006's business, not the abstract check's."""
    (tmp_path / "technote.toml").write_text('[technote]\nid = "SQR-000"\n')
    context = LintContext.from_dir(tmp_path, AuthorDb())
    assert check_abstract(context) == []


def test_conf_py_without_content_file_reports_tn006(tmp_path: Path) -> None:
    """A Sphinx technote with no index file yields TN006, not TN201."""
    (tmp_path / "technote.toml").write_text('[technote]\nid = "SQR-000"\n')
    (tmp_path / "conf.py").write_text(
        "from documenteer.conf.technote import *  # noqa: F401,F403\n"
    )
    (tmp_path / "requirements.txt").write_text("documenteer[technote]\n")
    context = LintContext.from_dir(tmp_path, AuthorDb())
    service = TechnoteLintService(context)
    findings = service.lint()
    assert [f.code for f in findings] == ["TN006"]
    assert findings[0].severity is Severity.error


def test_abstract_heading_rst_reports_tn202(tmp_path: Path) -> None:
    """An ``Abstract`` section heading in index.rst yields TN202."""
    content = """\
#############
Demo technote
#############

Abstract
========

A technote is a web-native single page document.

Introduction
============

Body text.
"""
    context = _context_with_content(tmp_path, "index.rst", content)
    findings = check_abstract(context)
    assert [f.code for f in findings] == ["TN202"]
    assert findings[0].severity is Severity.error
    assert findings[0].message.startswith("index.rst:5:")
    assert ".. abstract::" in findings[0].message


def test_abstract_heading_md_reports_tn202(tmp_path: Path) -> None:
    """A Markdown ``## Abstract`` heading in index.md yields TN202."""
    content = """\
# Demo technote

## Abstract

A technote is a web-native single page document.

## Introduction

Body text.
"""
    context = _context_with_content(tmp_path, "index.md", content)
    findings = check_abstract(context)
    assert [f.code for f in findings] == ["TN202"]
    assert findings[0].message.startswith("index.md:3:")
    # MyST content is pointed at the fenced abstract directive, not the rST
    # form.
    assert "```{abstract}" in findings[0].message
    assert ".. abstract::" not in findings[0].message


def test_abstract_heading_ipynb_reports_tn202(tmp_path: Path) -> None:
    """A ``## Abstract`` heading in an index.ipynb cell yields TN202."""
    content = _ipynb(
        "# Demo technote",
        "## Abstract\n\nA technote is a web-native single page document.",
        "## Introduction\n\nBody text.",
    )
    context = _context_with_content(tmp_path, "index.ipynb", content)
    findings = check_abstract(context)
    assert [f.code for f in findings] == ["TN202"]
    # Notebook content is pointed at the fenced abstract directive.
    assert "```{abstract}" in findings[0].message
    assert ".. abstract::" not in findings[0].message


def test_abstract_via_rst_include_passes(tmp_path: Path) -> None:
    """An abstract factored into an rST ``.. include::`` file passes."""
    (tmp_path / "abstract.rst").write_text(
        ".. abstract::\n\n   A web-native single page document.\n"
    )
    content = (
        "#############\nDemo technote\n#############\n\n"
        ".. include:: abstract.rst\n\n"
        "Introduction\n============\n\nBody text.\n"
    )
    context = _context_with_content(tmp_path, "index.rst", content)
    assert check_abstract(context) == []


def test_abstract_via_myst_include_passes(tmp_path: Path) -> None:
    """An abstract factored into a MyST ``{include}`` file passes."""
    (tmp_path / "abstract.md").write_text(
        "```{abstract}\nA web-native single page document.\n```\n"
    )
    content = (
        "# Demo technote\n\n"
        "```{include} abstract.md\n"
        "```\n\n"
        "## Introduction\n\nBody text.\n"
    )
    context = _context_with_content(tmp_path, "index.md", content)
    assert check_abstract(context) == []


def test_include_of_missing_file_reports_tn201(tmp_path: Path) -> None:
    """An include pointing at a missing file is ignored, not a crash."""
    content = (
        "#############\nDemo technote\n#############\n\n"
        ".. include:: nowhere.rst\n\n"
        "Introduction\n============\n\nBody text.\n"
    )
    context = _context_with_content(tmp_path, "index.rst", content)
    assert [f.code for f in check_abstract(context)] == ["TN201"]


def test_include_outside_technote_root_is_ignored(tmp_path: Path) -> None:
    """An include that escapes the technote root is not scanned."""
    (tmp_path / "abstract.rst").write_text(
        ".. abstract::\n\n   A web-native single page document.\n"
    )
    root = tmp_path / "technote"
    root.mkdir()
    content = (
        "#############\nDemo technote\n#############\n\n"
        ".. include:: ../abstract.rst\n\n"
        "Introduction\n============\n\nBody text.\n"
    )
    context = _context_with_content(root, "index.rst", content)
    assert [f.code for f in check_abstract(context)] == ["TN201"]


def test_empty_notebook_abstract_reports_tn204_without_line(
    tmp_path: Path,
) -> None:
    """A notebook's cells are concatenated, so no line number is reported."""
    content = _ipynb(
        "# Demo technote\n\n```{abstract}\n```",
        "## Introduction\n\nBody text.",
    )
    context = _context_with_content(tmp_path, "index.ipynb", content)
    findings = check_abstract(context)
    assert [f.code for f in findings] == ["TN204"]
    assert findings[0].message.startswith("index.ipynb: ")


def test_corrupt_notebook_reports_tn203(tmp_path: Path) -> None:
    """A content notebook that is not valid JSON yields a TN203 error."""
    context = _context_with_content(tmp_path, "index.ipynb", "{ not json")
    findings = check_abstract(context)
    assert [f.code for f in findings] == ["TN203"]
    assert findings[0].severity is Severity.error


def test_myst_options_only_abstract_reports_tn204(tmp_path: Path) -> None:
    """A MyST abstract directive with only options is treated as empty."""
    content = (
        "# Demo technote\n\n"
        "```{abstract}\n"
        ":class: dropdown\n"
        "```\n\n"
        "## Introduction\n\nBody text.\n"
    )
    context = _context_with_content(tmp_path, "index.md", content)
    assert [f.code for f in check_abstract(context)] == ["TN204"]


def test_rst_options_only_abstract_reports_tn204(tmp_path: Path) -> None:
    """An rST abstract directive with only options is treated as empty."""
    content = (
        "#############\nDemo technote\n#############\n\n"
        ".. abstract::\n"
        "   :class: dropdown\n\n"
        "Introduction\n============\n\nBody text.\n"
    )
    context = _context_with_content(tmp_path, "index.rst", content)
    assert [f.code for f in check_abstract(context)] == ["TN204"]


def test_setext_abstract_heading_md_reports_tn202(tmp_path: Path) -> None:
    """A Setext ``Abstract``/``----`` heading in index.md yields TN202."""
    content = (
        "# Demo technote\n\n"
        "Abstract\n--------\n\n"
        "A technote is a web-native single page document.\n\n"
        "## Introduction\n\nBody text.\n"
    )
    context = _context_with_content(tmp_path, "index.md", content)
    findings = check_abstract(context)
    assert [f.code for f in findings] == ["TN202"]
    assert "```{abstract}" in findings[0].message


def test_setext_abstract_heading_ipynb_reports_tn202(tmp_path: Path) -> None:
    """A Setext ``Abstract``/``====`` heading in a notebook yields TN202."""
    content = _ipynb(
        "# Demo technote",
        "Abstract\n========\n\n"
        "A technote is a web-native single page document.",
        "## Introduction\n\nBody text.",
    )
    context = _context_with_content(tmp_path, "index.ipynb", content)
    findings = check_abstract(context)
    assert [f.code for f in findings] == ["TN202"]


def test_abstract_finding_surfaces_through_lint(tmp_path: Path) -> None:
    """check_abstract's findings are aggregated by the service."""
    context = _context_with_content(
        tmp_path,
        "index.rst",
        "#####\nTitle\n#####\n\nIntroduction\n============\n\nBody.\n",
    )
    service = TechnoteLintService(context)
    assert [f.code for f in service.lint()] == ["TN201"]


def _context_with_requirements(
    tmp_path: Path, requirements_text: str
) -> LintContext:
    """Write a minimal technote.toml plus a requirements.txt, build a context.

    ``check_requirements`` reads only ``requirements_text``, so no content
    file is needed for these structural tests.
    """
    (tmp_path / "technote.toml").write_text('[technote]\nid = "SQR-000"\n')
    (tmp_path / "requirements.txt").write_text(requirements_text)
    return LintContext.from_dir(tmp_path, AuthorDb())


def test_sane_requirements_pass(tmp_path: Path) -> None:
    """documenteer[technote] with no separate sphinx pin has no findings."""
    context = _context_with_requirements(tmp_path, "documenteer[technote]\n")
    assert check_requirements(context) == []


def test_sane_requirements_with_floor_pin_pass(tmp_path: Path) -> None:
    """A version specifier on documenteer[technote] still passes."""
    context = _context_with_requirements(
        tmp_path,
        "# Project requirements\ndocumenteer[technote]>=1.0.0\n",
    )
    assert check_requirements(context) == []


def test_missing_documenteer_reports_tn002(tmp_path: Path) -> None:
    """requirements.txt without documenteer yields a TN002 warning."""
    context = _context_with_requirements(tmp_path, "sphinx-prompt\n")
    findings = check_requirements(context)
    assert [f.code for f in findings] == ["TN002"]
    assert findings[0].severity is Severity.warning


def test_documenteer_without_technote_extra_reports_tn002(
    tmp_path: Path,
) -> None:
    """Documenteer declared without the [technote] extra yields TN002."""
    context = _context_with_requirements(tmp_path, "documenteer\n")
    findings = check_requirements(context)
    assert [f.code for f in findings] == ["TN002"]
    assert findings[0].severity is Severity.warning


def test_documenteer_with_other_extra_reports_tn002(tmp_path: Path) -> None:
    """Documenteer with only a non-technote extra still yields TN002."""
    context = _context_with_requirements(tmp_path, "documenteer[guide]\n")
    assert [f.code for f in check_requirements(context)] == ["TN002"]


def test_documenteer_extra_aggregated_across_lines(tmp_path: Path) -> None:
    """The technote extra is honored even when split across two lines."""
    context = _context_with_requirements(
        tmp_path, "documenteer\ndocumenteer[technote]\n"
    )
    assert check_requirements(context) == []


def test_missing_requirements_file_reports_tn002(tmp_path: Path) -> None:
    """A technote directory with no requirements.txt yields TN002."""
    (tmp_path / "technote.toml").write_text('[technote]\nid = "SQR-000"\n')
    context = LintContext.from_dir(tmp_path, AuthorDb())
    assert [f.code for f in check_requirements(context)] == ["TN002"]


def test_sphinx_pinned_separately_reports_tn003(tmp_path: Path) -> None:
    """A separate sphinx requirement yields a TN003 warning."""
    context = _context_with_requirements(
        tmp_path, "documenteer[technote]\nsphinx==8.1.0\n"
    )
    findings = check_requirements(context)
    assert [f.code for f in findings] == ["TN003"]
    assert findings[0].severity is Severity.warning


def test_sphinx_declared_without_version_reports_tn003(tmp_path: Path) -> None:
    """An unversioned separate sphinx requirement still yields TN003."""
    context = _context_with_requirements(
        tmp_path, "documenteer[technote]\nSphinx\n"
    )
    assert [f.code for f in check_requirements(context)] == ["TN003"]


def test_requirements_drift_reports_both_warnings(tmp_path: Path) -> None:
    """Missing documenteer[technote] and a separate sphinx pin both fire."""
    context = _context_with_requirements(tmp_path, "sphinx==8.1.0\n")
    findings = check_requirements(context)
    assert [f.code for f in findings] == ["TN002", "TN003"]
    assert all(f.severity is Severity.warning for f in findings)


def test_requirements_findings_surface_through_lint(
    tmp_path: Path,
) -> None:
    """check_requirements' warnings are aggregated by the service."""
    (tmp_path / "technote.toml").write_text('[technote]\nid = "SQR-000"\n')
    (tmp_path / "index.rst").write_text(RST_WITH_ABSTRACT)
    (tmp_path / "requirements.txt").write_text("sphinx==8.1.0\n")
    context = LintContext.from_dir(tmp_path, AuthorDb())
    service = TechnoteLintService(context)
    findings = service.lint()
    # Warnings only (no author or abstract errors), so --strict would
    # promote exactly these to make the run fatal.
    assert [f.code for f in findings] == ["TN002", "TN003"]
    assert all(f.severity is Severity.warning for f in findings)
