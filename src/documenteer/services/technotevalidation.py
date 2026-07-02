"""Service for validating a technote's metadata and structure."""

from __future__ import annotations

import json
import re
import string
import tomllib
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from pydantic import ValidationError
from technote.sources.tomlsettings import TechnoteToml

from documenteer.storage.authordb import (
    AuthorDb,
    AuthorDbUnreachableError,
    AuthorNotFoundError,
)

__all__ = [
    "CHECKS",
    "Check",
    "Severity",
    "TechnoteValidationService",
    "ValidationContext",
    "ValidationFinding",
    "check_abstract",
    "check_requirements",
]


class Severity(StrEnum):
    """The severity of a validation finding."""

    error = "error"
    warning = "warning"


@dataclass(frozen=True)
class Check:
    """Metadata describing a single validation check.

    The `CHECKS` registry, keyed by ``code``, is the single source of truth
    for every check's stable code, human-readable name, description, and
    default severity. The validation runner consults it when building
    findings, and a future exception-configuration layer can consult it to
    map codes onto overridden severities.
    """

    code: str
    name: str
    description: str
    severity: Severity


CHECKS: dict[str, Check] = {
    "TN001": Check(
        code="TN001",
        name="schema-conformance",
        description="technote.toml conforms to the technote schema.",
        severity=Severity.error,
    ),
    "TN002": Check(
        code="TN002",
        name="requirements-declare-documenteer-technote",
        description=(
            "requirements.txt declares documenteer with the [technote] extra."
        ),
        severity=Severity.warning,
    ),
    "TN003": Check(
        code="TN003",
        name="requirements-no-separate-sphinx-pin",
        description="requirements.txt does not pin Sphinx separately.",
        severity=Severity.warning,
    ),
    "TN004": Check(
        code="TN004",
        name="technote-toml-present",
        description="technote.toml exists in the technote directory.",
        severity=Severity.error,
    ),
    "TN005": Check(
        code="TN005",
        name="technote-toml-valid-toml",
        description="technote.toml is syntactically valid TOML.",
        severity=Severity.error,
    ),
    "TN101": Check(
        code="TN101",
        name="author-internal-id-present",
        description="Every author declares an internal_id.",
        severity=Severity.error,
    ),
    "TN102": Check(
        code="TN102",
        name="author-internal-id-known",
        description="Each author's internal_id resolves in the author DB.",
        severity=Severity.error,
    ),
    "TN103": Check(
        code="TN103",
        name="authordb-reachable",
        description="The author database is reachable for resolution.",
        severity=Severity.warning,
    ),
    "TN201": Check(
        code="TN201",
        name="abstract-present",
        description="The content declares a non-empty abstract directive.",
        severity=Severity.error,
    ),
    "TN202": Check(
        code="TN202",
        name="abstract-uses-directive",
        description=(
            "The abstract uses the abstract directive rather than an "
            "ordinary section heading."
        ),
        severity=Severity.error,
    ),
}


@dataclass(frozen=True)
class ValidationFinding:
    """A single finding produced by a validation check."""

    code: str
    severity: Severity
    message: str

    @classmethod
    def from_check(cls, code: str, message: str) -> ValidationFinding:
        """Build a finding for a registered check's default severity."""
        check = CHECKS[code]
        return cls(code=check.code, severity=check.severity, message=message)


class ValidationContext:
    """The files and services a technote validation run operates on.

    Discovers a technote's ``technote.toml``, content file, and
    ``requirements.txt`` within a directory and holds the `AuthorDb` used to
    resolve author identifiers. The ``technote.toml`` *text* is read eagerly
    when the file exists (``toml_text`` is ``None`` when it is missing, so the
    structural check TN004 can report it); parsing into a `TechnoteToml` model
    is deferred to `parse_toml` so the syntax check (TN005) and the
    schema-conformance check (TN001) can each report a failure as a finding.
    """

    _CONTENT_FILENAMES = ("index.rst", "index.md", "index.ipynb")

    def __init__(
        self,
        *,
        root_dir: Path,
        toml_path: Path,
        toml_text: str | None,
        content_path: Path | None,
        requirements_path: Path | None,
        requirements_text: str | None,
        author_db: AuthorDb,
    ) -> None:
        self.root_dir = root_dir
        self.toml_path = toml_path
        self.toml_text = toml_text
        self.content_path = content_path
        self.requirements_path = requirements_path
        self.requirements_text = requirements_text
        self.author_db = author_db

    @classmethod
    def from_dir(
        cls, root_dir: Path, author_db: AuthorDb
    ) -> ValidationContext:
        """Build a context from a technote directory."""
        toml_path = root_dir / "technote.toml"
        toml_text: str | None = None
        if toml_path.exists():
            toml_text = toml_path.read_text(encoding="utf-8")

        content_path: Path | None = None
        for filename in cls._CONTENT_FILENAMES:
            candidate = root_dir / filename
            if candidate.exists():
                content_path = candidate
                break

        requirements_file = root_dir / "requirements.txt"
        requirements_path: Path | None = None
        requirements_text: str | None = None
        if requirements_file.exists():
            requirements_path = requirements_file
            requirements_text = requirements_file.read_text(encoding="utf-8")

        return cls(
            root_dir=root_dir,
            toml_path=toml_path,
            toml_text=toml_text,
            content_path=content_path,
            requirements_path=requirements_path,
            requirements_text=requirements_text,
            author_db=author_db,
        )

    def parse_toml(self) -> TechnoteToml:
        """Parse the ``technote.toml`` text into a `TechnoteToml` model.

        Raises
        ------
        tomllib.TOMLDecodeError
            If the ``technote.toml`` is not syntactically valid TOML.
        pydantic.ValidationError
            If the ``technote.toml`` is valid TOML but does not conform to the
            schema.
        """
        if self.toml_text is None:
            raise RuntimeError("technote.toml text was not read")
        return TechnoteToml.parse_toml(self.toml_text)


class TechnoteValidationService:
    """Validate a technote's metadata, producing a list of findings."""

    def __init__(self, context: ValidationContext) -> None:
        self._context = context

    def validate(self) -> list[ValidationFinding]:
        """Run the registered checks and aggregate their findings."""
        findings: list[ValidationFinding] = []

        # TN004 — technote.toml must exist. A missing file short-circuits the
        # remaining checks because they all read the parsed metadata.
        if self._context.toml_text is None:
            return [
                ValidationFinding.from_check(
                    "TN004",
                    f"technote.toml not found in {self._context.root_dir}.",
                )
            ]

        # TN005/TN001 — the technote.toml must be valid TOML (TN005) and then
        # conform to the schema (TN001). Either failure short-circuits the
        # remaining checks because they operate on the parsed model.
        try:
            parsed = self._context.parse_toml()
        except tomllib.TOMLDecodeError as e:
            return [
                ValidationFinding.from_check(
                    "TN005",
                    f"technote.toml is not valid TOML: {e}",
                )
            ]
        except ValidationError as e:
            return [
                ValidationFinding.from_check(
                    "TN001",
                    f"technote.toml does not conform to the schema: {e}",
                )
            ]

        findings.extend(self._check_author_internal_ids(parsed))
        findings.extend(check_abstract(self._context))
        findings.extend(check_requirements(self._context))
        return findings

    def _check_author_internal_ids(
        self, parsed: TechnoteToml
    ) -> list[ValidationFinding]:
        """Check author ``internal_id`` metadata (TN101/TN102/TN103)."""
        findings: list[ValidationFinding] = []
        for author in parsed.technote.authors:
            name = f"{author.name.given} {author.name.family}".strip()
            if author.internal_id is None:
                findings.append(
                    ValidationFinding.from_check(
                        "TN101",
                        f"Author {name} is missing an internal_id.",
                    )
                )
                continue
            try:
                self._context.author_db.get_author(author.internal_id)
            except AuthorNotFoundError:
                findings.append(
                    ValidationFinding.from_check(
                        "TN102",
                        f"Author {name} has internal_id "
                        f"'{author.internal_id}', which is not in the "
                        f"author database.",
                    )
                )
            except AuthorDbUnreachableError:
                findings.append(
                    ValidationFinding.from_check(
                        "TN103",
                        f"Could not reach the author database to verify "
                        f"internal_id '{author.internal_id}' for author "
                        f"{name}.",
                    )
                )
            except ValidationError:
                findings.append(
                    ValidationFinding.from_check(
                        "TN102",
                        f"Author {name} has internal_id "
                        f"'{author.internal_id}', whose author database "
                        f"record is malformed.",
                    )
                )
        return findings


# The reStructuredText abstract directive: ``.. abstract::``.
_RST_ABSTRACT_DIRECTIVE = re.compile(r"^\s*\.\.\s+abstract::\s*$")
# A reStructuredText title line reading exactly "Abstract" (case-insensitive).
_RST_ABSTRACT_TITLE = re.compile(r"^\s*abstract\s*$", re.IGNORECASE)
# MyST abstract directives: ```` ```{abstract} ```` and ``:::{abstract}``.
_MYST_BACKTICK_ABSTRACT = re.compile(r"^\s*`{3,}\{abstract\}\s*$")
_MYST_COLON_ABSTRACT = re.compile(r"^\s*:{3,}\{abstract\}\s*$")
# Closing fences for the corresponding MyST directives.
_BACKTICK_FENCE = re.compile(r"^\s*`{3,}\s*$")
_COLON_FENCE = re.compile(r"^\s*:{3,}\s*$")
# A Markdown ATX heading reading exactly "Abstract" (case-insensitive).
_MD_ABSTRACT_HEADING = re.compile(r"^\s*#{1,6}\s+abstract\s*$", re.IGNORECASE)
# A Markdown Setext heading underline: a line of only ``=`` or only ``-``.
_MD_SETEXT_UNDERLINE = re.compile(r"^\s*(=+|-+)\s*$")
# A MyST/rST directive *option* line, e.g. ``:class: dropdown``. These are
# directive configuration, not body content, so an options-only abstract is
# still empty.
_DIRECTIVE_OPTION_LINE = re.compile(r"^\s*:[\w-]+:")


def check_abstract(context: ValidationContext) -> list[ValidationFinding]:
    """Statically check that the technote content declares an abstract.

    Locates ``index.{rst,md,ipynb}`` via the context's content path and
    scans its source (no Sphinx build) for a non-empty abstract directive.
    Three outcomes are distinguished (TN2xx content checks):

    - A non-empty abstract *directive* (rST ``.. abstract::``; MyST
      ```` ```{abstract} ```` or ``:::{abstract}``; ``.ipynb`` markdown
      cells) → no findings.
    - No directive but an ordinary ``Abstract`` section heading → a TN202
      finding pointing authors to the format's abstract directive.
    - Neither → a TN201 finding: no abstract found.

    The suggested-directive text in the TN201/TN202 messages is format-aware:
    reStructuredText content is pointed at ``.. abstract::`` and MyST/notebook
    content at the ```` ```{abstract} ```` fenced directive.
    """
    content_path = context.content_path
    if content_path is None:
        return [
            ValidationFinding.from_check(
                "TN201",
                "No abstract found: the technote has no "
                "index.{rst,md,ipynb} content file to scan.",
            )
        ]

    suffix = content_path.suffix.lower()
    if suffix == ".ipynb":
        text = _read_notebook_markdown(content_path)
        is_rst = False
    else:
        text = content_path.read_text(encoding="utf-8")
        is_rst = suffix == ".rst"

    if is_rst:
        has_directive = _has_rst_abstract_directive(text)
        has_heading = _has_rst_abstract_heading(text)
        directive_hint = ".. abstract::"
    else:
        has_directive = _has_myst_abstract_directive(text)
        has_heading = _has_markdown_abstract_heading(text)
        directive_hint = "```{abstract}```"

    if has_directive:
        return []
    if has_heading:
        return [
            ValidationFinding.from_check(
                "TN202",
                f"{content_path.name} declares its abstract as an ordinary "
                f"'Abstract' section heading. Use the {directive_hint} "
                f"directive instead so the abstract is captured in the "
                f"technote metadata.",
            )
        ]
    return [
        ValidationFinding.from_check(
            "TN201",
            f"No abstract found in {content_path.name}. Add a non-empty "
            f"{directive_hint} directive so the abstract is captured in the "
            f"technote metadata.",
        )
    ]


def check_requirements(context: ValidationContext) -> list[ValidationFinding]:
    """Statically check the technote's ``requirements.txt`` (TN002/TN003).

    Parses ``ValidationContext.requirements_text`` with
    `packaging.requirements.Requirement` and emits structural findings:

    - TN002 (warning) if ``documenteer`` is absent or is declared without
      the ``[technote]`` extra — the technote build needs
      ``documenteer[technote]`` to pull in the technote theme and config.
    - TN003 (warning) if ``sphinx`` is declared as its own requirement.
      ``documenteer[technote]`` already constrains Sphinx to a supported
      range, so pinning it separately risks drifting out of that window.

    A missing ``requirements.txt`` (no ``requirements_text``) is treated as
    an empty file, so ``documenteer`` is absent and TN002 fires.
    """
    findings: list[ValidationFinding] = []
    requirements = _parse_requirements(context.requirements_text or "")

    documenteer_reqs = [
        req
        for req in requirements
        if canonicalize_name(req.name) == "documenteer"
    ]
    # Aggregate extras across *every* documenteer line, so a bare
    # ``documenteer`` followed by ``documenteer[technote]`` still counts the
    # technote extra as declared.
    extras = {
        extra.lower() for req in documenteer_reqs for extra in req.extras
    }
    if not documenteer_reqs or "technote" not in extras:
        findings.append(
            ValidationFinding.from_check(
                "TN002",
                "requirements.txt should declare 'documenteer[technote]' so "
                "the technote theme and Sphinx configuration are installed.",
            )
        )

    if any(canonicalize_name(req.name) == "sphinx" for req in requirements):
        findings.append(
            ValidationFinding.from_check(
                "TN003",
                "requirements.txt pins 'sphinx' separately. Remove it and "
                "rely on the Sphinx version constrained by "
                "'documenteer[technote]' to avoid version drift.",
            )
        )

    return findings


def _parse_requirements(text: str) -> list[Requirement]:
    """Parse the parseable requirement lines from ``requirements.txt`` text.

    Blank lines, comments, and pip option lines (for example ``-r`` or
    ``--index-url``) are skipped, as are lines that are not valid PEP 508
    requirements (for example editable VCS or URL installs).
    """
    requirements: list[Requirement] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", "-")):
            continue
        # Drop an inline comment (a '#' preceded by whitespace) before parsing.
        line = re.split(r"\s+#", line, maxsplit=1)[0].strip()
        if not line:
            continue
        try:
            requirements.append(Requirement(line))
        except InvalidRequirement:
            continue
    return requirements


def _read_notebook_markdown(path: Path) -> str:
    """Concatenate the source of every markdown cell in a notebook."""
    data = json.loads(path.read_text(encoding="utf-8"))
    parts: list[str] = []
    for cell in data.get("cells", []):
        if cell.get("cell_type") != "markdown":
            continue
        source = cell.get("source", "")
        if isinstance(source, list):
            parts.append("".join(source))
        else:
            parts.append(source)
    return "\n\n".join(parts)


def _has_rst_abstract_directive(text: str) -> bool:
    """Whether the text has a non-empty ``.. abstract::`` directive."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not _RST_ABSTRACT_DIRECTIVE.match(line):
            continue
        marker_indent = len(line) - len(line.lstrip())
        # The directive body is the indented block that follows. An indented,
        # non-blank line that is not an option line counts as content, making
        # the directive non-empty. Option lines (``:class: dropdown``) are
        # directive configuration, so an options-only directive stays empty.
        for body_line in lines[i + 1 :]:
            if body_line.strip() == "":
                continue
            indent = len(body_line) - len(body_line.lstrip())
            if indent <= marker_indent:
                break
            if _DIRECTIVE_OPTION_LINE.match(body_line):
                continue
            return True
    return False


def _has_myst_abstract_directive(text: str) -> bool:
    """Whether the text has a non-empty MyST abstract directive."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if _MYST_BACKTICK_ABSTRACT.match(line):
            if _myst_fence_has_body(lines, i, _BACKTICK_FENCE):
                return True
        elif _MYST_COLON_ABSTRACT.match(line):
            if _myst_fence_has_body(lines, i, _COLON_FENCE):
                return True
    return False


def _myst_fence_has_body(
    lines: list[str], open_index: int, closer: re.Pattern[str]
) -> bool:
    """Whether a MyST fenced directive has non-blank body before it closes.

    Option lines (``:class: dropdown``) are directive configuration rather
    than body content, so a directive containing only options is still empty.
    """
    for line in lines[open_index + 1 :]:
        if closer.match(line):
            return False
        if _DIRECTIVE_OPTION_LINE.match(line):
            continue
        if line.strip():
            return True
    return False


def _has_rst_abstract_heading(text: str) -> bool:
    """Whether the text has an ``Abstract`` reStructuredText section title."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not _RST_ABSTRACT_TITLE.match(line):
            continue
        title_len = len(line.strip())
        if i + 1 < len(lines) and _is_rst_adornment(lines[i + 1], title_len):
            return True
    return False


def _is_rst_adornment(line: str, min_length: int) -> bool:
    """Whether a line is a reStructuredText title adornment underline."""
    stripped = line.rstrip()
    if len(stripped) < min_length or not stripped:
        return False
    char = stripped[0]
    if char not in string.punctuation:
        return False
    return all(c == char for c in stripped)


def _has_markdown_abstract_heading(text: str) -> bool:
    """Whether the text has a Markdown ``Abstract`` heading.

    Detects both ATX headings (``## Abstract``) and Setext headings (an
    ``Abstract`` line underlined by ``===`` or ``---``).
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if _MD_ABSTRACT_HEADING.match(line):
            return True
        if (
            _RST_ABSTRACT_TITLE.match(line)
            and i + 1 < len(lines)
            and _MD_SETEXT_UNDERLINE.match(lines[i + 1])
        ):
            return True
    return False
