"""Tests for the TechnoteValidationService class."""

from __future__ import annotations

import json
from pathlib import Path

import pytest_responses  # noqa: F401
import requests
from responses import RequestsMock

from documenteer.services.technotevalidation import (
    Severity,
    TechnoteValidationService,
    ValidationContext,
    check_abstract,
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


def _write_technote(tmp_path: Path, toml_content: str) -> ValidationContext:
    """Write a technote.toml into ``tmp_path`` and build a context.

    Also writes an ``index.rst`` with a well-formed abstract so the
    content-group abstract check (TN201/TN202) stays silent and these
    metadata-focused tests observe only author/schema findings.
    """
    (tmp_path / "technote.toml").write_text(toml_content)
    (tmp_path / "index.rst").write_text(
        "#####\nTitle\n#####\n\n.. abstract::\n\n   An abstract.\n"
    )
    return ValidationContext.from_dir(tmp_path, AuthorDb())


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
    service = TechnoteValidationService(context, context.author_db)
    findings = service.validate()
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
    service = TechnoteValidationService(context, context.author_db)
    findings = service.validate()
    assert [f.code for f in findings] == ["TN101", "TN101"]
    assert all(f.severity is Severity.error for f in findings)


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
    service = TechnoteValidationService(context, context.author_db)
    findings = service.validate()
    assert [f.code for f in findings] == ["TN102"]
    assert findings[0].severity is Severity.error


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
    service = TechnoteValidationService(context, context.author_db)
    findings = service.validate()
    assert [f.code for f in findings] == ["TN103"]
    assert findings[0].severity is Severity.warning


def test_invalid_schema_short_circuits(tmp_path: Path) -> None:
    """A schema failure yields only TN001 and skips the author check."""
    context = _write_technote(
        tmp_path,
        """
[technote]
id = "SQR-000"

[[technote.authors]]
name.given = "Jonathan"
""",
    )
    service = TechnoteValidationService(context, context.author_db)
    findings = service.validate()
    assert [f.code for f in findings] == ["TN001"]
    assert findings[0].severity is Severity.error


def _context_with_content(
    tmp_path: Path, filename: str, content: str
) -> ValidationContext:
    """Write a minimal technote.toml plus a content file, build a context."""
    (tmp_path / "technote.toml").write_text('[technote]\nid = "SQR-000"\n')
    (tmp_path / filename).write_text(content)
    return ValidationContext.from_dir(tmp_path, AuthorDb())


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


def test_empty_abstract_directive_reports_tn201(tmp_path: Path) -> None:
    """An abstract directive with no body is not a passing abstract."""
    content = "# Demo technote\n\n```{abstract}\n```\n\n## Introduction\n"
    context = _context_with_content(tmp_path, "index.md", content)
    findings = check_abstract(context)
    assert [f.code for f in findings] == ["TN201"]


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


def test_missing_content_file_reports_tn201(tmp_path: Path) -> None:
    """A technote directory with no index file yields TN201."""
    (tmp_path / "technote.toml").write_text('[technote]\nid = "SQR-000"\n')
    context = ValidationContext.from_dir(tmp_path, AuthorDb())
    assert [f.code for f in check_abstract(context)] == ["TN201"]


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
    assert ".. abstract::" in findings[0].message


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
    assert ".. abstract::" in findings[0].message


def test_abstract_finding_surfaces_through_validate(tmp_path: Path) -> None:
    """check_abstract's findings are aggregated by the service."""
    context = _context_with_content(
        tmp_path,
        "index.rst",
        "#####\nTitle\n#####\n\nIntroduction\n============\n\nBody.\n",
    )
    service = TechnoteValidationService(context, context.author_db)
    assert [f.code for f in service.validate()] == ["TN201"]
