"""Service for linting a technote's metadata and structure."""

from __future__ import annotations

import json
import re
import string
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from pydantic import ValidationError
from technote.sources.tomlsettings import Person, TechnoteToml

from documenteer.storage.authordb import (
    AuthorDb,
    AuthorDbUnreachableError,
    AuthorNotFoundError,
    AuthorSearchResult,
)

__all__ = [
    "CHECKS",
    "Check",
    "LintContext",
    "LintFinding",
    "Severity",
    "TechnoteLintService",
    "check_abstract",
    "check_requirements",
]


class Severity(StrEnum):
    """The severity of a lint finding."""

    error = "error"
    warning = "warning"


@dataclass(frozen=True)
class Check:
    """Metadata describing a single lint check.

    The `CHECKS` registry, keyed by ``code``, is the single source of truth
    for every check's stable code, human-readable name, description, and
    default severity. The lint runner consults it when building
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
    "TN006": Check(
        code="TN006",
        name="content-file-present",
        description=(
            "A Sphinx technote has an index.rst, index.md, or index.ipynb "
            "content file."
        ),
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
        description="The content declares an abstract directive.",
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
    "TN203": Check(
        code="TN203",
        name="content-file-parseable",
        description="The content file can be parsed to scan for an abstract.",
        severity=Severity.error,
    ),
    "TN204": Check(
        code="TN204",
        name="abstract-directive-not-empty",
        description="The abstract directive has body content.",
        severity=Severity.error,
    ),
}


_NAME_MATCH_SCORE = 90.0
"""The author-search relevance score that counts as a name match.

Ook documents its 0-100 search scores in bands and describes 90-100 as "exact
or near-exact matches", so a *single* result in that band identifies an author
confidently enough to suggest. Two or more are ambiguous (for example the
several ``Jones`` entries a family-name-only query returns), and the
suggestion is withheld.
"""


@dataclass(frozen=True)
class _AuthorSuggestion:
    """A confidently-matched author database entry to suggest to the user."""

    internal_id: str
    name: str
    basis: str

    def describe(self, declared_name: str) -> str:
        """Phrase the suggestion for appending to a finding's message.

        The database's own spelling of the name is included only when it
        differs from the name the technote declares, where it is the evidence
        that makes an unfamiliar ID recognizable (``jonesrl`` is "R. Lynne
        Jones"); repeating an identical name would only pad the message.
        """
        if _normalize_name(self.name) == _normalize_name(declared_name):
            return (
                f"Did you mean '{self.internal_id}' (matched by {self.basis})?"
            )
        return (
            f"Did you mean '{self.internal_id}' "
            f"({self.name}, matched by {self.basis})?"
        )


@dataclass(frozen=True)
class LintFinding:
    """A single finding produced by a lint check."""

    code: str
    severity: Severity
    message: str

    @classmethod
    def from_check(cls, code: str, message: str) -> LintFinding:
        """Build a finding for a registered check's default severity."""
        check = CHECKS[code]
        return cls(code=check.code, severity=check.severity, message=message)


class LintContext:
    """The files and services a technote lint run operates on.

    Discovers a technote's ``technote.toml``, content file, Sphinx
    ``conf.py``, and ``requirements.txt`` within a directory and holds the
    `AuthorDb` used to resolve author identifiers. The ``technote.toml`` *text*
    is read eagerly when the file exists (``toml_text`` is ``None`` when it is
    missing, so the structural check TN004 can report it); parsing into a
    `TechnoteToml` model is deferred to `parse_toml` so the syntax check
    (TN005) and the schema-conformance check (TN001) can each report a failure
    as a finding.

    The presence of a content file or a ``conf.py`` also distinguishes a Sphinx
    technote from a technote-series repository that is built by some other
    tool; see `is_sphinx_technote`.
    """

    _CONTENT_FILENAMES = ("index.rst", "index.md", "index.ipynb")

    def __init__(
        self,
        *,
        root_dir: Path,
        toml_path: Path,
        toml_text: str | None,
        content_path: Path | None,
        conf_path: Path | None,
        requirements_path: Path | None,
        requirements_text: str | None,
        author_db: AuthorDb,
    ) -> None:
        self.root_dir = root_dir
        self.toml_path = toml_path
        self.toml_text = toml_text
        self.content_path = content_path
        self.conf_path = conf_path
        self.requirements_path = requirements_path
        self.requirements_text = requirements_text
        self.author_db = author_db

    @classmethod
    def from_dir(cls, root_dir: Path, author_db: AuthorDb) -> LintContext:
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

        conf_file = root_dir / "conf.py"
        conf_path = conf_file if conf_file.exists() else None

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
            conf_path=conf_path,
            requirements_path=requirements_path,
            requirements_text=requirements_text,
            author_db=author_db,
        )

    @property
    def is_sphinx_technote(self) -> bool:
        """Whether the directory is a Sphinx-built technote.

        A directory with neither a content file nor a ``conf.py`` is a
        technote-series repository that is built by some other tool (for
        example an org-mode deck published through the shared technote CI with
        a custom build command). Only the ``technote.toml``-based checks apply
        to it; the requirements, content, and content-file checks assume a
        Documenteer/Sphinx build.
        """
        return self.content_path is not None or self.conf_path is not None

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


class TechnoteLintService:
    """Validate a technote's metadata, producing a list of findings."""

    def __init__(self, context: LintContext) -> None:
        self._context = context

    def lint(self) -> list[LintFinding]:
        """Run the registered checks and aggregate their findings.

        Only the checks that read the parsed `TechnoteToml` model are skipped
        when ``technote.toml`` cannot be parsed. A ``technote.toml`` that is
        unreadable as TOML (TN005) or that fails schema validation (TN001)
        therefore still gets its requirements (TN002/TN003) and content
        (TN2xx) findings reported, so a technote's other problems are visible
        in the same run rather than hidden behind the metadata failure. A
        directory with no ``technote.toml`` at all (TN004) is not a technote,
        so that finding stands alone.

        A directory with neither a content file nor a ``conf.py`` is a
        technote-series repository that Sphinx does not build (see
        `LintContext.is_sphinx_technote`). Only the
        ``technote.toml``-based checks — TN004/TN005/TN001 and the author
        checks — run for it, so a healthy non-Sphinx technote reports nothing.
        """
        findings: list[LintFinding] = []

        # TN004 — technote.toml must exist. A missing file short-circuits the
        # remaining checks because the directory is not a technote.
        if self._context.toml_text is None:
            return [
                LintFinding.from_check(
                    "TN004",
                    f"technote.toml not found in {self._context.root_dir}.",
                )
            ]

        # TN005/TN001 — the technote.toml must be valid TOML (TN005) and then
        # conform to the schema (TN001). Either failure leaves the parsed
        # model unavailable, so only the checks that need it are skipped.
        parsed: TechnoteToml | None = None
        try:
            parsed = self._context.parse_toml()
        except tomllib.TOMLDecodeError as e:
            findings.append(
                LintFinding.from_check(
                    "TN005",
                    f"technote.toml is not valid TOML: {e}",
                )
            )
        except ValidationError as e:
            findings.append(
                _schema_conformance_finding(self._context.toml_text, e)
            )

        if parsed is not None:
            findings.extend(self._check_author_internal_ids(parsed))

        # A technote that Sphinx does not build has no requirements.txt or
        # content-file contract to check, so the technote.toml-based checks
        # above are the whole report.
        if not self._context.is_sphinx_technote:
            return findings

        # TN006 — a Sphinx technote needs a content file for Sphinx to build
        # and for the abstract scan to read.
        if self._context.content_path is None:
            findings.append(
                LintFinding.from_check(
                    "TN006",
                    f"No content file found in {self._context.root_dir}: a "
                    f"technote needs an index.rst, index.md, or index.ipynb "
                    f"file.",
                )
            )
        findings.extend(check_abstract(self._context))
        findings.extend(check_requirements(self._context))
        return findings

    def _check_author_internal_ids(
        self, parsed: TechnoteToml
    ) -> list[LintFinding]:
        """Check author ``internal_id`` metadata (TN101/TN102/TN103)."""
        findings: list[LintFinding] = []
        for author in parsed.technote.authors:
            name = f"{author.name.given} {author.name.family}".strip()
            if author.internal_id is None:
                message = f"Author {name} is missing an internal_id."
                suggestion = self._suggest_internal_id(author)
                if suggestion is not None:
                    message += (
                        f" {suggestion.describe(name)} Run 'documenteer "
                        f"technote sync-authors' after adding it."
                    )
                findings.append(LintFinding.from_check("TN101", message))
                continue
            try:
                self._context.author_db.get_author(author.internal_id)
            except AuthorNotFoundError:
                message = (
                    f"Author {name} has internal_id '{author.internal_id}', "
                    f"which is not in the author database."
                )
                suggestion = self._suggest_internal_id(author)
                if suggestion is not None:
                    message += f" {suggestion.describe(name)}"
                findings.append(LintFinding.from_check("TN102", message))
            except AuthorDbUnreachableError:
                findings.append(
                    LintFinding.from_check(
                        "TN103",
                        f"Could not reach the author database to verify "
                        f"internal_id '{author.internal_id}' for author "
                        f"{name}.",
                    )
                )
            except ValidationError:
                findings.append(
                    LintFinding.from_check(
                        "TN102",
                        f"Author {name} has internal_id "
                        f"'{author.internal_id}', whose author database "
                        f"record is malformed.",
                    )
                )
        return findings

    def _suggest_internal_id(self, author: Person) -> _AuthorSuggestion | None:
        """Look up the ``internal_id`` an author most likely meant.

        Searches the author database by name (Ook's author API has no ORCID
        lookup) and accepts a candidate only on a confident match: the same
        ORCID, or a single near-exact name match with no conflicting ORCID.
        Anything ambiguous, and any failure of the lookup itself, yields
        `None` so the finding keeps its plain message — a suggestion is a
        convenience and must never turn a working lint run into a
        failing one.
        """
        query = ", ".join(
            part for part in (author.name.family, author.name.given) if part
        )
        if not query:
            return None
        try:
            results = self._context.author_db.search_authors(query)
        except ValueError:
            # Both an unreachable database (AuthorDbUnreachableError) and a
            # malformed search response (pydantic ValidationError) are
            # ValueErrors, and neither should disturb the primary check.
            return None
        declared_orcid = (
            str(author.orcid) if author.orcid is not None else None
        )
        return _match_author(results, orcid=declared_orcid)


def _match_author(
    results: list[AuthorSearchResult], *, orcid: str | None
) -> _AuthorSuggestion | None:
    """Pick the one author search result that confidently matches.

    An ORCID declared in ``technote.toml`` is the strongest evidence: a single
    result carrying the same ORCID is a match however its name is spelled.
    Otherwise a single result in the search's near-exact score band matches by
    name, unless it declares a *different* ORCID than the technote does, which
    proves the two are different people. Every other outcome — no results,
    several equally-good ones, a name match contradicted by an ORCID — is
    ambiguous and returns `None`.
    """
    declared_orcid = _normalize_orcid(orcid)
    if declared_orcid is not None:
        orcid_matches = [
            result
            for result in results
            if _normalize_orcid(result.orcid) == declared_orcid
        ]
        if len(orcid_matches) == 1:
            return _suggestion_from(orcid_matches[0], basis="ORCID")
        if orcid_matches:
            return None

    name_matches = [
        result for result in results if result.score >= _NAME_MATCH_SCORE
    ]
    if len(name_matches) != 1:
        return None
    candidate = name_matches[0]
    candidate_orcid = _normalize_orcid(candidate.orcid)
    if (
        declared_orcid is not None
        and candidate_orcid is not None
        and candidate_orcid != declared_orcid
    ):
        return None
    return _suggestion_from(candidate, basis="name")


def _suggestion_from(
    result: AuthorSearchResult, *, basis: str
) -> _AuthorSuggestion:
    """Build a suggestion from an author search result."""
    name = " ".join(
        part for part in (result.given_name, result.family_name) if part
    )
    return _AuthorSuggestion(
        internal_id=result.internal_id, name=name, basis=basis
    )


def _normalize_orcid(orcid: object) -> str | None:
    """Reduce an ORCID URL to its bare identifier for comparison.

    Comparing identifiers rather than URLs makes the match insensitive to the
    ``http``/``https`` scheme and to a trailing slash.
    """
    if orcid is None:
        return None
    return str(orcid).rstrip("/").rsplit("/", maxsplit=1)[-1].upper()


def _normalize_name(name: str) -> str:
    """Fold a personal name for comparing two spellings of it."""
    return " ".join(name.lower().split())


# The reStructuredText abstract directive marker: ``.. abstract::``, with any
# text that trails it on the marker line. docutils lowercases directive names,
# so ``.. Abstract::`` builds too.
_RST_ABSTRACT_DIRECTIVE = re.compile(
    r"^(?P<indent>\s*)\.\.\s+abstract::(?P<trailing>.*)$", re.IGNORECASE
)
# A reStructuredText title line reading exactly "Abstract" (case-insensitive).
_RST_ABSTRACT_TITLE = re.compile(r"^\s*abstract\s*$", re.IGNORECASE)
# MyST abstract directives: ```` ```{abstract} ```` and ``:::{abstract}``.
# Matched case-insensitively because docutils lowercases directive names.
_MYST_BACKTICK_ABSTRACT = re.compile(
    r"^\s*`{3,}\{abstract\}\s*$", re.IGNORECASE
)
_MYST_COLON_ABSTRACT = re.compile(r"^\s*:{3,}\{abstract\}\s*$", re.IGNORECASE)
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
# Include directives, whose target is scanned for an abstract as well: rST
# ``.. include:: path`` and MyST ```` ```{include} path ```` / ``:::{include}
# path``.
_RST_INCLUDE_DIRECTIVE = re.compile(
    r"^\s*\.\.\s+include::\s*(?P<path>\S.*?)\s*$", re.IGNORECASE
)
_MYST_INCLUDE_DIRECTIVE = re.compile(
    r"^\s*(?:`{3,}|:{3,})\{include\}\s*(?P<path>\S.*?)\s*$", re.IGNORECASE
)


@dataclass(frozen=True)
class _DirectiveScan:
    """The outcome of scanning one source for an abstract directive.

    Three outcomes are distinguished: no directive at all (``found`` false and
    ``empty_line`` ``None``), a directive whose body is empty (``empty_line``
    holds the 1-indexed line of its marker), and a non-empty directive
    (``found`` true).
    """

    found: bool
    empty_line: int | None = None


@dataclass(frozen=True)
class _FormatRules:
    """How one markup format is scanned for an abstract, and described.

    ``directive_hint`` names the format's abstract directive in a finding's
    message, and ``empty_advice`` completes the TN204 message that a present
    directive has no body.
    """

    scan_directive: Callable[[str], _DirectiveScan]
    find_heading: Callable[[str], int | None]
    include_pattern: re.Pattern[str]
    directive_hint: str
    empty_advice: str


@dataclass(frozen=True)
class _Source:
    """One body of text scanned for an abstract.

    ``name`` is how the source is identified in a finding. ``locatable`` is
    false for a notebook, whose markdown cells are concatenated before
    scanning, so line numbers in the scanned text locate nothing in the file.
    """

    name: str
    text: str
    locatable: bool = True

    def locate(self, line: int) -> str:
        """Format the ``file:line:`` prefix for a line in this source."""
        if not self.locatable:
            return f"{self.name}: "
        return f"{self.name}:{line}: "


@dataclass(frozen=True)
class _AbstractSearch:
    """What scanning a content file and its includes turned up.

    At most one of the fields is set, in priority order: a non-empty directive
    anywhere wins (``found``); otherwise the first empty directive
    (``empty_location``); otherwise the first ``Abstract`` heading
    (``heading_location``). The locations are preformatted ``file:line:``
    prefixes.
    """

    found: bool = False
    empty_location: str | None = None
    heading_location: str | None = None


def _search_abstract(
    sources: list[_Source], rules: _FormatRules
) -> _AbstractSearch:
    """Scan each source for an abstract directive, then for a heading."""
    empty_location: str | None = None
    heading_location: str | None = None
    for source in sources:
        scan = rules.scan_directive(source.text)
        if scan.found:
            return _AbstractSearch(found=True)
        if empty_location is None and scan.empty_line is not None:
            empty_location = source.locate(scan.empty_line)
        if heading_location is None:
            heading_line = rules.find_heading(source.text)
            if heading_line is not None:
                heading_location = source.locate(heading_line)
    return _AbstractSearch(
        empty_location=empty_location, heading_location=heading_location
    )


def check_abstract(context: LintContext) -> list[LintFinding]:
    """Statically check that the technote content declares an abstract.

    Locates ``index.{rst,md,ipynb}`` via the context's content path and
    scans its source (no Sphinx build) for a non-empty abstract directive.
    Five outcomes are distinguished (TN2xx content checks):

    - A non-empty abstract *directive* (rST ``.. abstract::``; MyST
      ```` ```{abstract} ```` or ``:::{abstract}``; ``.ipynb`` markdown
      cells) → no findings.
    - A directive that is present but has no body → a TN204 finding locating
      the directive marker. The common cause is an abstract left unindented
      under ``.. abstract::``, which docutils reads as an empty directive and
      which publishes an empty abstract section.
    - No directive but an ordinary ``Abstract`` section heading → a TN202
      finding locating the heading and pointing authors to the format's
      abstract directive.
    - None of the above → a TN201 finding: no abstract found.
    - A ``.ipynb`` file that is not valid JSON → a TN203 finding: the content
      file could not be parsed to scan for an abstract.

    The suggested-directive text in the messages is format-aware:
    reStructuredText content is pointed at ``.. abstract::`` and MyST/notebook
    content at the ```` ```{abstract} ```` fenced directive.

    An abstract that the content factors into another file and pulls in with
    an include directive is found as well; see `_included_sources`.

    TN202 and TN204 findings are prefixed with a ``file:line:`` location. A
    notebook's markdown cells are concatenated before scanning, so its
    findings carry the file name alone rather than a line number that does not
    correspond to anything in the file.

    A directory with no content file at all produces no findings here: that is
    a structural condition, reported as TN006 by the lint runner.
    """
    content_path = context.content_path
    if content_path is None:
        return []

    suffix = content_path.suffix.lower()
    if suffix == ".ipynb":
        try:
            text = _read_notebook_markdown(content_path)
        except json.JSONDecodeError as e:
            return [
                LintFinding.from_check(
                    "TN203",
                    f"{content_path.name} could not be parsed as a notebook "
                    f"(invalid JSON): {e}",
                )
            ]
        is_rst = False
    else:
        text = content_path.read_text(encoding="utf-8")
        is_rst = suffix == ".rst"

    rules = _RST_RULES if is_rst else _MYST_RULES
    sources = [_Source(content_path.name, text, locatable=suffix != ".ipynb")]
    sources.extend(
        _included_sources(
            text,
            content_path=content_path,
            root_dir=context.root_dir,
            pattern=rules.include_pattern,
        )
    )
    search = _search_abstract(sources, rules)

    if search.found:
        return []
    if search.empty_location is not None:
        return [
            LintFinding.from_check(
                "TN204",
                f"{search.empty_location}the {rules.directive_hint} directive "
                f"is empty — {rules.empty_advice}",
            )
        ]
    if search.heading_location is not None:
        return [
            LintFinding.from_check(
                "TN202",
                f"{search.heading_location}the abstract is declared as an "
                f"ordinary 'Abstract' section heading. Use the "
                f"{rules.directive_hint} directive instead so the abstract is "
                f"captured in the technote metadata.",
            )
        ]
    return [
        LintFinding.from_check(
            "TN201",
            f"No abstract found in {content_path.name}. Add a non-empty "
            f"{rules.directive_hint} directive so the abstract is captured in "
            f"the technote metadata.",
        )
    ]


def _included_sources(
    text: str, *, content_path: Path, root_dir: Path, pattern: re.Pattern[str]
) -> list[_Source]:
    """Read the files the content includes, one level deep.

    A technote may factor its abstract into a separate file pulled in with an
    include directive, so those files are scanned for an abstract too. The
    resolution is deliberately shallow — includes within an included file are
    not followed — because this is a source scan, not a full parse.

    Paths are resolved relative to the content file's directory (or, for the
    rST convention of a leading ``/``, relative to the technote root). A path
    that escapes the technote root is skipped, as is one that cannot be read:
    Sphinx reports a broken include itself, and the linter should not fail
    on it twice.
    """
    root = root_dir.resolve()
    sources: list[_Source] = []
    for line in text.splitlines():
        match = pattern.match(line)
        if match is None:
            continue
        raw_path = match.group("path")
        if raw_path.startswith("/"):
            candidate = root_dir.joinpath(*raw_path.lstrip("/").split("/"))
        else:
            candidate = content_path.parent / raw_path
        resolved = candidate.resolve()
        if (
            not resolved.is_relative_to(root)
            or resolved == content_path.resolve()
        ):
            continue
        try:
            included_text = resolved.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        sources.append(_Source(str(resolved.relative_to(root)), included_text))
    return sources


def check_requirements(context: LintContext) -> list[LintFinding]:
    """Statically check the technote's ``requirements.txt`` (TN002/TN003).

    Parses ``LintContext.requirements_text`` with
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
    findings: list[LintFinding] = []
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
            LintFinding.from_check(
                "TN002",
                "requirements.txt should declare 'documenteer[technote]' so "
                "the technote theme and Sphinx configuration are installed.",
            )
        )

    if any(canonicalize_name(req.name) == "sphinx" for req in requirements):
        findings.append(
            LintFinding.from_check(
                "TN003",
                "requirements.txt pins 'sphinx' separately. Remove it and "
                "rely on the Sphinx version constrained by "
                "'documenteer[technote]' to avoid version drift.",
            )
        )

    return findings


# Guidance shared by every legacy author-name hint.
_MODERN_NAME_ADVICE = (
    'Use \'name = { given = "Given", family = "Family" }\' instead. Run '
    "'documenteer technote migrate' to update technote.toml to the modern "
    "format automatically."
)

# Historical ``[[technote.authors]]`` name forms, as the keys that identify
# each form in the ``name`` table paired with the hint describing it.
_LEGACY_NAME_HINTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (
        ("name",),
        "Its [[technote.authors]] entries use the legacy single-string "
        "author name form 'name = { name = \"Full Name\" }', which technote "
        "0.5 removed.",
    ),
    (
        ("given_names", "family_names"),
        "Its [[technote.authors]] entries use the pre-technote-0.5 author "
        'name keys \'name = { given_names = "...", '
        'family_names = "..." }\', which were renamed in November 2023.',
    ),
)


def _schema_conformance_finding(
    toml_text: str, error: ValidationError
) -> LintFinding:
    """Build the TN001 finding for a schema-invalid ``technote.toml``.

    When the ``[[technote.authors]]`` entries use one of the historical author
    name forms, the raw pydantic report is prefixed with a message that names
    the legacy form, shows its modern replacement, and points at
    :command:`documenteer technote migrate`. The pydantic detail is always
    appended so schema errors that are not about legacy author names remain
    actionable.
    """
    hints = _legacy_author_name_hints(toml_text)
    if not hints:
        return LintFinding.from_check(
            "TN001",
            f"technote.toml does not conform to the schema: {error}",
        )
    return LintFinding.from_check(
        "TN001",
        "technote.toml does not conform to the schema. "
        + " ".join(hints)
        + f" {_MODERN_NAME_ADVICE} Underlying schema errors: {error}",
    )


def _legacy_author_name_hints(toml_text: str) -> list[str]:
    """Describe the legacy author-name forms present in technote.toml text.

    Reads the *input* data (rather than the parsed model, which is
    unavailable when schema validation fails) and returns one hint for each
    distinct historical ``[[technote.authors]]`` name form found. Authors
    whose schema errors are unrelated to these forms produce no hints.
    """
    name_tables = _author_name_tables(toml_text)
    return [
        hint
        for keys, hint in _LEGACY_NAME_HINTS
        if any(key in name_table for name_table in name_tables for key in keys)
    ]


def _author_name_tables(toml_text: str) -> list[dict[str, Any]]:
    """Extract the ``name`` tables of each ``[[technote.authors]]`` entry."""
    data = tomllib.loads(toml_text)
    technote_table = data.get("technote")
    if not isinstance(technote_table, dict):
        return []
    authors = technote_table.get("authors")
    if not isinstance(authors, list):
        return []
    return [
        author["name"]
        for author in authors
        if isinstance(author, dict) and isinstance(author.get("name"), dict)
    ]


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
    """Concatenate the source of every markdown cell in a notebook.

    Raises
    ------
    json.JSONDecodeError
        If the notebook file is not valid JSON. Callers translate this into a
        TN203 finding rather than letting it propagate as a traceback.
    """
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


def _scan_rst_abstract_directive(text: str) -> _DirectiveScan:
    """Scan reStructuredText for an ``.. abstract::`` directive.

    Distinguishes a non-empty directive from one whose body is missing (the
    common case being a body left unindented at column 0, which docutils
    reads as an empty directive and which publishes an empty abstract).
    """
    empty_line: int | None = None
    lines = text.splitlines()
    for i, line in enumerate(lines):
        match = _RST_ABSTRACT_DIRECTIVE.match(line)
        if match is None:
            continue
        # Text trailing the marker is body content: the directive declares no
        # arguments and no options, so docutils folds the whole directive
        # block into its content.
        if match.group("trailing").strip():
            return _DirectiveScan(found=True)
        marker_indent = len(match.group("indent"))
        # Otherwise the directive body is the indented block that follows. An
        # indented, non-blank line that is not an option line counts as
        # content. Option lines (``:class: dropdown``) are directive
        # configuration, so an options-only directive stays empty.
        if _rst_block_has_body(lines[i + 1 :], marker_indent):
            return _DirectiveScan(found=True)
        if empty_line is None:
            empty_line = i + 1
    return _DirectiveScan(found=False, empty_line=empty_line)


def _rst_block_has_body(lines: list[str], marker_indent: int) -> bool:
    """Whether the indented block after a directive marker has content."""
    for body_line in lines:
        if body_line.strip() == "":
            continue
        indent = len(body_line) - len(body_line.lstrip())
        if indent <= marker_indent:
            return False
        if _DIRECTIVE_OPTION_LINE.match(body_line):
            continue
        return True
    return False


def _scan_myst_abstract_directive(text: str) -> _DirectiveScan:
    """Scan MyST/Markdown for a fenced abstract directive.

    Like the reStructuredText scan, distinguishes a directive that is missing
    from one that is present but has no body between its fences.
    """
    empty_line: int | None = None
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if _MYST_BACKTICK_ABSTRACT.match(line):
            closer = _BACKTICK_FENCE
        elif _MYST_COLON_ABSTRACT.match(line):
            closer = _COLON_FENCE
        else:
            continue
        if _myst_fence_has_body(lines, i, closer):
            return _DirectiveScan(found=True)
        if empty_line is None:
            empty_line = i + 1
    return _DirectiveScan(found=False, empty_line=empty_line)


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


def _find_rst_abstract_heading(text: str) -> int | None:
    """Find an ``Abstract`` reStructuredText section title.

    Returns the 1-indexed line of the title, or `None` if there is none.
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not _RST_ABSTRACT_TITLE.match(line):
            continue
        title_len = len(line.strip())
        if i + 1 < len(lines) and _is_rst_adornment(lines[i + 1], title_len):
            return i + 1
    return None


def _is_rst_adornment(line: str, min_length: int) -> bool:
    """Whether a line is a reStructuredText title adornment underline."""
    stripped = line.rstrip()
    if len(stripped) < min_length or not stripped:
        return False
    char = stripped[0]
    if char not in string.punctuation:
        return False
    return all(c == char for c in stripped)


def _find_markdown_abstract_heading(text: str) -> int | None:
    """Find a Markdown ``Abstract`` heading.

    Detects both ATX headings (``## Abstract``) and Setext headings (an
    ``Abstract`` line underlined by ``===`` or ``---``), returning the
    1-indexed line of the heading text, or `None` if there is none.
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if _MD_ABSTRACT_HEADING.match(line):
            return i + 1
        if (
            _RST_ABSTRACT_TITLE.match(line)
            and i + 1 < len(lines)
            and _MD_SETEXT_UNDERLINE.match(lines[i + 1])
        ):
            return i + 1
    return None


_RST_RULES = _FormatRules(
    scan_directive=_scan_rst_abstract_directive,
    find_heading=_find_rst_abstract_heading,
    include_pattern=_RST_INCLUDE_DIRECTIVE,
    directive_hint="'.. abstract::'",
    empty_advice="indent the abstract text under the directive.",
)
"""How reStructuredText content is scanned for an abstract."""

_MYST_RULES = _FormatRules(
    scan_directive=_scan_myst_abstract_directive,
    find_heading=_find_markdown_abstract_heading,
    include_pattern=_MYST_INCLUDE_DIRECTIVE,
    directive_hint="'```{abstract}' fenced",
    empty_advice=(
        "put the abstract text between the opening and closing fences."
    ),
)
"""How MyST Markdown and notebook content is scanned for an abstract."""
