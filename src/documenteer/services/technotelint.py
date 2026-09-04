"""Service for linting a technote's metadata and structure."""

from __future__ import annotations

import re
import tomllib
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from docutils import nodes
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from pydantic import ValidationError
from technote.ext.abstract import AbstractNode
from technote.sources.tomlsettings import (
    LINT_RULE_CODE_PATTERN,
    Person,
    TechnoteToml,
)

from documenteer.citations import normalize_doi, orcid_url
from documenteer.services.technotecff import (
    CFF_FILENAME,
    CffStatus,
    TechnoteCffService,
)
from documenteer.services.technoteread import (
    TechnoteDocument,
    TechnoteReadError,
    read_technote,
)
from documenteer.storage.authordb import (
    Author,
    AuthorDb,
    AuthorDbUnreachableError,
    AuthorNotFoundError,
    AuthorSearchResult,
    normalize_orcid,
)
from documenteer.storage.datacite import (
    DataCiteClient,
    DataCiteCreator,
    DataCiteRecord,
    DataCiteUnavailableError,
)
from documenteer.storage.technotetoml import TechnoteTomlFile

__all__ = [
    "CHECKS",
    "Check",
    "IgnoreSource",
    "IgnoredRule",
    "LintContext",
    "LintFinding",
    "Severity",
    "TechnoteLintService",
    "check_abstract",
    "check_requirements",
    "rule_url",
]

DOCS_BASE_URL = "https://documenteer.lsst.io/technotes/lint"
"""Base URL for Documenteer's own lint rule documentation pages."""


def _documenteer_rule_url(code: str) -> str:
    """Return the Documenteer landing page URL a rule code documents at."""
    return f"{DOCS_BASE_URL}/{code.lower()}.html"


def rule_url(code: str) -> str:
    """Return the documentation landing page URL for a lint rule code.

    A registered rule answers with its own `Check.docs_url`, so a rule set
    that documents itself somewhere other than Documenteer is linked where it
    actually lives. An unregistered code falls back to the Documenteer page
    its name would have.
    """
    check = CHECKS.get(code)
    if check is not None:
        return check.docs_url
    return _documenteer_rule_url(code)


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
    docs_url: str = ""
    """The page that documents this rule, and that a finding links to.

    Left empty, it defaults to the Documenteer page for the code — where
    every rule in this registry is documented today. A rule set that
    documents itself elsewhere (a future ``technote``-package rule set, say)
    sets it, so the code stays the stable identifier while the page that
    explains it can move.
    """

    def __post_init__(self) -> None:
        if not self.docs_url:
            object.__setattr__(
                self, "docs_url", _documenteer_rule_url(self.code)
            )


CHECKS: dict[str, Check] = {
    # ``TN`` rules check what any technote needs; ``R`` rules check Rubin's
    # conventions and services. A code carries its rule set's prefix, so it
    # says which set owns it and does not have to change when the generic
    # rules move into the technote package and this file keeps the Rubin
    # ones. The hundreds families mean the same thing in both prefixes:
    # 0xx structure and configuration, 1xx metadata, 2xx content.
    "TN001": Check(
        code="TN001",
        name="schema-conformance",
        description="technote.toml conforms to the technote schema.",
        severity=Severity.error,
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
    "TN007": Check(
        code="TN007",
        name="lint-configuration-valid",
        description=(
            "The [technote.lint] table names rules the linter knows."
        ),
        severity=Severity.warning,
    ),
    # TN104 (doi-well-formed) was retired before it shipped: technote 0.10.0
    # validates and normalizes [technote] doi inside TechnoteToml.parse_toml,
    # so a value that is not a DOI is a schema-conformance failure (TN001)
    # and never reaches a rule of its own. Codes are stable identifiers, so
    # the gap stays rather than renumbering TN105/TN106.
    "TN105": Check(
        code="TN105",
        name="datacite-metadata-current",
        description=(
            "The metadata registered for the DOI matches the technote."
        ),
        severity=Severity.warning,
    ),
    "TN106": Check(
        code="TN106",
        name="citation-cff-current",
        description="CITATION.cff matches what technote.toml generates.",
        severity=Severity.error,
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
        name="document-readable",
        description="Sphinx can read the technote's document.",
        severity=Severity.error,
    ),
    "TN204": Check(
        code="TN204",
        name="abstract-directive-not-empty",
        description="The abstract directive has body content.",
        severity=Severity.error,
    ),
    # The Rubin rule set. Each of these needs something beyond technote.toml
    # and the technote package: R002/R003 encode Rubin's technote packaging
    # convention, and R101-R103 resolve authors against the Rubin author
    # database.
    "R002": Check(
        code="R002",
        name="requirements-declare-documenteer-technote",
        description=(
            "requirements.txt declares documenteer with the [technote] extra."
        ),
        severity=Severity.warning,
    ),
    "R003": Check(
        code="R003",
        name="requirements-no-separate-sphinx-pin",
        description="requirements.txt does not pin Sphinx separately.",
        severity=Severity.warning,
    ),
    "R101": Check(
        code="R101",
        name="author-internal-id-present",
        description="Every author declares an internal_id.",
        severity=Severity.error,
    ),
    "R102": Check(
        code="R102",
        name="author-internal-id-known",
        description="Each author's internal_id resolves in the author DB.",
        severity=Severity.error,
    ),
    "R103": Check(
        code="R103",
        name="authordb-reachable",
        description="The author database is reachable for resolution.",
        severity=Severity.warning,
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

    def fix_hint(self) -> str:
        """Name the command that acts on this suggestion.

        An ORCID match is one ``sync-authors`` can act on by itself: it
        resolves the *same* declared ORCID and fills the ``internal_id`` in,
        so the message sends the writer straight there. A name match is only
        a suggestion for a human to verify and type in, so the sync still
        comes after that edit.
        """
        if self.basis == "ORCID":
            return "Run 'documenteer technote sync-authors' to add it."
        return "Run 'documenteer technote sync-authors' after adding it."


class IgnoreSource(StrEnum):
    """Where a rule's ignore instruction was configured.

    The value is how the source is named in the lint report, so a reader of
    CI output can find the place to change.
    """

    toml = "technote.toml [technote.lint]"
    cli = "--ignore"


@dataclass(frozen=True)
class IgnoredRule:
    """A rule this lint run skips, and where it was told to."""

    code: str
    source: IgnoreSource


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
    `AuthorDb` used to resolve author identifiers, along with the
    `DataCiteClient` TN105 asks what a DOI is registered as. The
    ``technote.toml`` *text* is read eagerly when the file exists
    (``toml_text`` is ``None`` when it is missing, so the structural check
    TN004 can report it); parsing into a `TechnoteToml` model is deferred to
    `parse_toml` so the syntax check (TN005) and the schema-conformance check
    (TN001) can each report a failure as a finding.

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
        datacite: DataCiteClient | None = None,
    ) -> None:
        self.root_dir = root_dir
        self.toml_path = toml_path
        self.toml_text = toml_text
        self.content_path = content_path
        self.conf_path = conf_path
        self.requirements_path = requirements_path
        self.requirements_text = requirements_text
        self.author_db = author_db
        self.datacite = datacite if datacite is not None else DataCiteClient()
        self._document: TechnoteDocument | None = None
        self._read_error: TechnoteReadError | None = None
        self._read_attempted = False

    @classmethod
    def from_dir(
        cls,
        root_dir: Path,
        author_db: AuthorDb,
        datacite: DataCiteClient | None = None,
    ) -> LintContext:
        """Build a context from a technote directory.

        ``datacite`` defaults to a client with the standard short timeout;
        pass one to override it.
        """
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
            datacite=datacite,
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

    def read_document(self) -> TechnoteDocument:
        """Read the technote's document with Sphinx, at most once per run.

        Several rules need what the *built* technote says rather than what
        ``technote.toml`` declares — the title a document resolves from its
        H1, and the abstract the ``abstract`` directive publishes. They all
        share this one read, and share its failure too: a technote Sphinx
        cannot read fails once and every caller sees the same error.

        Raises
        ------
        TechnoteReadError
            Raised if the technote cannot be read. The message carries
            Sphinx's own diagnosis.
        """
        if not self._read_attempted:
            self._read_attempted = True
            try:
                self._document = read_technote(self.root_dir)
            except TechnoteReadError as e:
                self._read_error = e
        if self._read_error is not None:
            raise self._read_error
        if self._document is None:  # pragma: no cover - unreachable
            raise RuntimeError("the technote read produced no document")
        return self._document

    @property
    def document_title(self) -> str | None:
        """The title the technote's own document resolves to.

        `None` when the technote cannot be read at all. A rule that compares
        titles then has nothing to compare and says nothing: the read failure
        is TN203's to report, once, rather than every title rule's.
        """
        try:
            return self.read_document().title
        except TechnoteReadError:
            return None

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
    """Validate a technote's metadata, producing a list of findings.

    Parameters
    ----------
    context
        The files and services this run reads.
    ignore
        Rule codes to skip, from outside ``technote.toml`` — the command
        line's ``--ignore`` option. They add to the codes the technote's own
        ``[technote.lint] ignore`` names rather than replacing them.
    """

    def __init__(
        self, context: LintContext, *, ignore: Sequence[str] = ()
    ) -> None:
        self._context = context
        self._ignored, self._ignore_findings = _resolve_ignores(
            context, ignore
        )
        self._ignored_codes = frozenset(rule.code for rule in self._ignored)

    @property
    def ignored_rules(self) -> list[IgnoredRule]:
        """The rules this run skips, in code order.

        A report names these so that CI output shows a rule is *off* rather
        than passing.
        """
        return list(self._ignored)

    def is_enabled(self, code: str) -> bool:
        """Whether a rule runs in this lint run.

        A check consults this before doing work that costs something — TN105's
        DataCite request, the author checks' author-database lookups — so an
        ignored rule is not merely silent but never leaves the machine.
        """
        return code not in self._ignored_codes

    def lint(self) -> list[LintFinding]:
        """Run the enabled checks and aggregate their findings.

        Rules named by ``[technote.lint] ignore`` and by the ``ignore``
        argument report nothing: the ignore set is applied once, here, both
        by gating the checks that cost network requests and by filtering
        whatever the remaining checks produce, so no ignored finding can
        escape by a route a check forgot to gate. A configuration this cannot
        make sense of is reported as TN007 rather than dropped, and the valid
        entries still apply.

        Only the checks that read the parsed `TechnoteToml` model are skipped
        when ``technote.toml`` cannot be parsed. A ``technote.toml`` that is
        unreadable as TOML (TN005) or that fails schema validation (TN001)
        therefore still gets its requirements (R002/R003) and content
        (TN2xx) findings reported, so a technote's other problems are visible
        in the same run rather than hidden behind the metadata failure. A
        directory with no ``technote.toml`` at all (TN004) is not a technote,
        so that finding stands alone.

        A directory with neither a content file nor a ``conf.py`` is a
        technote-series repository that Sphinx does not build (see
        `LintContext.is_sphinx_technote`). Only the
        ``technote.toml``-based checks — TN004/TN005/TN001 and the metadata
        checks (TN1xx/R1xx) — run for it, so a healthy non-Sphinx technote
        reports nothing.
        """
        return [
            finding
            for finding in self._collect_findings()
            if self.is_enabled(finding.code)
        ]

    def _collect_findings(self) -> list[LintFinding]:
        """Run every enabled check, in the order their findings report."""
        # TN007 — whatever the ignore configuration itself got wrong. It is
        # reported like any other finding, and can itself be ignored: a
        # writer who lists TN007 has asked not to hear about their own
        # configuration.
        findings: list[LintFinding] = list(self._ignore_findings)

        # TN004 — technote.toml must exist. A missing file short-circuits the
        # remaining checks because the directory is not a technote.
        if self._context.toml_text is None:
            findings.append(
                LintFinding.from_check(
                    "TN004",
                    f"technote.toml not found in {self._context.root_dir}.",
                )
            )
            return findings

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
            # Gated rather than filtered: TN105 reads the registered metadata
            # over the network, and an ignored rule must not spend a request
            # on a finding that is thrown away.
            if self.is_enabled("TN105"):
                findings.extend(_check_datacite(parsed, self._context))
            if self.is_enabled("TN106"):
                findings.extend(_check_citation_cff(self._context))

        # A technote that Sphinx does not build has no requirements.txt or
        # content-file contract to check, so the technote.toml-based checks
        # above are the whole report.
        if not self._context.is_sphinx_technote:
            return findings

        # TN006 — a Sphinx technote needs a content file for Sphinx to build
        # and for the abstract check to read.
        if self._context.content_path is None:
            findings.append(
                LintFinding.from_check(
                    "TN006",
                    f"No content file found in {self._context.root_dir}: a "
                    f"technote needs an index.rst, index.md, or index.ipynb "
                    f"file.",
                )
            )
        elif parsed is not None:
            # The content checks read the document through the technote's own
            # Sphinx build, which cannot be configured from a technote.toml
            # that does not parse. TN005 or TN001 has already reported that,
            # and reporting the document as unreadable (TN203) would say the
            # same thing a second time, in words that point at the wrong file.
            findings.extend(check_abstract(self._context))
        findings.extend(check_requirements(self._context))
        return findings

    def _check_author_internal_ids(
        self, parsed: TechnoteToml
    ) -> list[LintFinding]:
        """Check author ``internal_id`` metadata (R101/R102/R103).

        Every branch that would reach the author database is gated on the
        rule it reports, so ignoring R101-R103 leaves the run offline: the
        resolution lookup is what R102 and R103 are, and the suggestion
        lookup only ever decorates an R101 or R102 message.
        """
        findings: list[LintFinding] = []
        for author in parsed.technote.authors:
            name = f"{author.name.given} {author.name.family}".strip()
            internal_id = author.internal_id
            if internal_id is None:
                if self.is_enabled("R101"):
                    findings.append(self._missing_id_finding(author, name))
                continue
            findings.extend(
                self._resolve_internal_id(author, name, internal_id)
            )
        return findings

    def _missing_id_finding(self, author: Person, name: str) -> LintFinding:
        """Report an author that declares no ``internal_id`` (R101)."""
        message = f"Author {name} is missing an internal_id."
        suggestion = self._suggest_internal_id(author)
        if suggestion is not None:
            message += f" {suggestion.describe(name)} {suggestion.fix_hint()}"
        return LintFinding.from_check("R101", message)

    def _resolve_internal_id(
        self, author: Person, name: str, internal_id: str
    ) -> list[LintFinding]:
        """Resolve a declared ``internal_id`` against the author database.

        The one lookup serves both rules it can report — R102 for an ID the
        database does not hold, R103 for a database that cannot answer — so
        it is worth making while either is enabled, and skipped entirely when
        neither is.
        """
        if not (self.is_enabled("R102") or self.is_enabled("R103")):
            return []
        try:
            self._context.author_db.get_author(internal_id)
        except AuthorNotFoundError:
            if not self.is_enabled("R102"):
                return []
            message = (
                f"Author {name} has internal_id '{internal_id}', "
                f"which is not in the author database."
            )
            suggestion = self._suggest_internal_id(author)
            if suggestion is not None:
                message += f" {suggestion.describe(name)}"
            return [LintFinding.from_check("R102", message)]
        except AuthorDbUnreachableError:
            if not self.is_enabled("R103"):
                return []
            return [
                LintFinding.from_check(
                    "R103",
                    f"Could not reach the author database to verify "
                    f"internal_id '{internal_id}' for author {name}.",
                )
            ]
        except ValidationError:
            if not self.is_enabled("R102"):
                return []
            return [
                LintFinding.from_check(
                    "R102",
                    f"Author {name} has internal_id '{internal_id}', whose "
                    f"author database record is malformed.",
                )
            ]
        return []

    def _suggest_internal_id(self, author: Person) -> _AuthorSuggestion | None:
        """Look up the ``internal_id`` an author most likely meant.

        A declared ORCID is tried first, against the author database's exact
        ORCID lookup: it is the one globally unique, author-supplied
        identifier here, so a hit is a match however differently the technote
        and the database spell the name. Anything else — no declared ORCID, an
        ORCID nobody holds, or a failed lookup — falls back to a name search,
        which suggests only a single near-exact match with no conflicting
        ORCID.

        Anything ambiguous, and any failure of either lookup, yields `None` so
        the finding keeps its plain message — a suggestion is a convenience
        and must never turn a working lint run into a failing one.
        """
        declared_orcid = (
            str(author.orcid) if author.orcid is not None else None
        )
        if declared_orcid is not None:
            match = self._lookup_by_orcid(declared_orcid)
            if match is not None:
                return _suggestion_from(match, basis="ORCID")
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
        return _match_author(results, orcid=declared_orcid)

    def _lookup_by_orcid(self, orcid: str) -> Author | None:
        """Resolve a declared ORCID exactly, or `None` if it does not."""
        try:
            return self._context.author_db.get_author_by_orcid(orcid)
        except ValueError:
            # An ORCID the database rejects (InvalidOrcidError), an
            # unreachable database (AuthorDbUnreachableError), and a malformed
            # response (pydantic ValidationError) are all ValueErrors, and
            # none of them should disturb the primary check.
            return None


def _resolve_ignores(
    context: LintContext, cli_codes: Sequence[str]
) -> tuple[list[IgnoredRule], list[LintFinding]]:
    """Resolve the rules a run skips, and report a configuration it cannot use.

    The technote's own ``[technote.lint] ignore`` and the command line's
    ``--ignore`` are additive: a rule either source names is skipped, and a
    rule both name is attributed to the file, which is the durable of the
    two. Every entry is validated against the `CHECKS` registry, so a rule
    set that adds, retires, or renames a code needs no second list of code
    names kept in step with it.

    A code that names no rule is returned as a TN007 finding rather than
    raised or dropped: a mistyped code must not stop a lint run, and it must
    not silently leave a rule on that the writer believes is off. A file
    entry of the wrong *shape* is technote's schema violation (TN001).
    """
    findings: list[LintFinding] = []
    rules: dict[str, IgnoredRule] = {}
    file_setting, file_findings = _file_ignore_setting(context)
    findings.extend(file_findings)
    for source, raw in (
        (IgnoreSource.toml, file_setting),
        (IgnoreSource.cli, list(cli_codes)),
    ):
        if raw is None:
            continue
        codes, entry_findings = _validate_ignore_codes(raw, source)
        findings.extend(entry_findings)
        for code in codes:
            rules.setdefault(code, IgnoredRule(code=code, source=source))
    return [rules[code] for code in sorted(rules)], findings


def _file_ignore_setting(
    context: LintContext,
) -> tuple[Any, list[LintFinding]]:
    """Read the raw ``[technote.lint] ignore`` value from technote.toml.

    The file is read with Documenteer's own tomlkit-backed reader rather than
    through technote's parsed model, because the configuration has to be
    available even when the rest of the file fails schema validation
    (TN001) — a technote may well be ignoring a rule *about* the metadata
    that fails. The table's *shape* is technote's to validate, though: since
    technote 0.11.0 owns the ``[technote.lint]`` schema, a setting that is
    not a table, an ``ignore`` that is not an array, or an entry that is not
    a rule code is a TN001 finding, and this reader skips it without a
    finding of its own rather than reporting the same mistake twice.

    A file that is not valid TOML yields nothing and no finding of its own:
    TN005 already reports it, and there is no configuration to read out of a
    file that cannot be parsed.
    """
    if context.toml_text is None:
        return None, []
    try:
        toml_file = TechnoteTomlFile(context.toml_text)
    except ValueError:
        # tomlkit's ParseError is a ValueError; TN005 reports the file.
        return None, []
    settings = toml_file.lint_settings
    if settings is None or not isinstance(settings, dict):
        # A [technote.lint] that is not a table fails technote's schema, so
        # TN001 reports it; there is no configuration to read out of it.
        return None, []
    return settings.get("ignore"), []


def _validate_ignore_codes(
    raw: Any, source: IgnoreSource
) -> tuple[list[str], list[LintFinding]]:
    """Validate one source's ignore entries against the `CHECKS` registry.

    Every entry is judged on its own: an entry that names no rule is
    reported and skipped, and the valid entries around it still apply.

    The two sources are held to different standards on *shape*. technote
    owns the ``[technote.lint]`` schema (since 0.11.0) and validates it when
    the file is parsed: an ``ignore`` that is not an array, an entry that is
    not a string, or a code that is not an uppercase prefix followed by a
    number (``LINT_RULE_CODE_PATTERN``) fails schema validation and is
    reported as TN001. Those entries are skipped here without a second
    finding, and the file's codes are matched exactly as technote accepts
    them. ``--ignore`` has no schema but this one, so a mistyped command-line
    entry is reported as TN007, and its case is folded for convenience.
    """
    if isinstance(raw, str) or not isinstance(raw, list | tuple):
        if source is IgnoreSource.toml:
            return [], []
        return [], [
            LintFinding.from_check(
                "TN007",
                f"The ignore setting in {source} must be an array of rule "
                f"codes, not {_describe_toml_type(raw)}. No rules are "
                f"ignored from it.",
            )
        ]

    if source is IgnoreSource.toml and not all(
        isinstance(entry, str) and LINT_RULE_CODE_PATTERN.match(entry)
        for entry in raw
    ):
        # technote rejects the whole file for one bad entry, and TN001
        # reports it; honouring the entries around it would switch rules off
        # on the strength of a table technote has said is invalid.
        return [], []

    codes: list[str] = []
    findings: list[LintFinding] = []
    for entry in raw:
        if not isinstance(entry, str):
            findings.append(
                LintFinding.from_check(
                    "TN007",
                    f"The ignore setting in {source} lists {entry!r}, which "
                    f"is not a rule code. Entries are strings such as "
                    f"'TN105'; the other entries still apply.",
                )
            )
            continue
        code = entry if source is IgnoreSource.toml else entry.strip().upper()
        if code not in CHECKS:
            findings.append(
                LintFinding.from_check(
                    "TN007",
                    f"'{entry}' in {source} is not a lint rule code, so no "
                    f"rule is ignored for it.",
                )
            )
            continue
        codes.append(code)
    return codes, findings


def _describe_toml_type(value: Any) -> str:
    """Name a TOML value's type as the file's writer would recognize it."""
    if isinstance(value, bool):
        return "a boolean"
    if isinstance(value, str):
        return "a string"
    if isinstance(value, int):
        return "an integer"
    if isinstance(value, float):
        return "a float"
    if isinstance(value, dict):
        return "a table"
    if isinstance(value, list | tuple):
        return "an array"
    return f"a {type(value).__name__}"


def _check_citation_cff(context: LintContext) -> list[LintFinding]:
    """Check that an adopted CITATION.cff still matches technote.toml (TN106).

    The comparison is the one `TechnoteCffService` performs for
    ``documenteer technote sync-cff --check``: the file is regenerated
    from ``technote.toml`` — and from the title the technote's document
    resolves, exactly as the command does — and compared with what is on
    disk, so the linter and that CI gate can never disagree about whether a
    file is stale. Generation is deterministic, which is what makes a content
    comparison meaningful.

    A repository with no CITATION.cff is silent, and is answered before the
    technote is read at all: adoption is opt-in per repository, so an absent
    file means the repository has not asked for one rather than that it is
    missing something, and a repository that has not opted in should not pay
    for a Sphinx run to be told so.

    A ``technote.toml`` that cannot be composed into a citation at all — one
    declaring an author with no name, say — is silent too. Staleness is not
    the finding to report about it, and TN001 has already reported the schema
    failure underneath.
    """
    cff_path = context.root_dir / CFF_FILENAME
    if not cff_path.is_file():
        return []
    try:
        service = TechnoteCffService.from_technote_toml(
            context.toml_path, document_title=context.document_title
        )
    except ValueError:
        return []
    if service.status(cff_path) is not CffStatus.stale:
        return []
    return [
        LintFinding.from_check(
            "TN106",
            f"{CFF_FILENAME} is out of date with technote.toml. Run "
            "'documenteer technote sync-cff' to regenerate it.",
        )
    ]


def _check_datacite(
    parsed: TechnoteToml, context: LintContext
) -> list[LintFinding]:
    """Check the technote against the DOI's registered metadata (TN105).

    This rule leaves the machine, as the author checks do, but it is the only
    one that degrades to silence: an unreachable author database is reported
    as R103, because an unresolved ``internal_id`` blocks a DOI from being
    minted, while an unreachable DataCite is reported as nothing. *Not*
    answering is therefore a first-class outcome here rather than an
    afterthought, and the check is silent — no finding, and no noise about
    the attempt — whenever it cannot reach a confident conclusion:

    - the technote declares no DOI, so there is nothing to cross-check;
    - the DOI is not a DOI. `TechnoteToml.parse_toml` validates the field, so
      such a value is a schema-conformance failure (TN001) and never reaches
      this rule with a parsed model; the `normalize_doi` guard here only
      keeps TN105 quiet rather than raising if Documenteer's normalizer and
      technote's ever disagree about what counts as a DOI;
    - DataCite answers 404, which is what a DOI that has been reserved but
      not yet made findable looks like;
    - DataCite cannot be reached at all — no network, DNS failure, timeout,
      an outage, or a response that is not a DOI record. A technote author
      working on a plane gets a clean lint run.

    Both comparisons are deliberately tolerant, because a false positive here
    is worse than a miss: this rule warns about metadata registered by the
    DOI minter, which the person reading the finding may not control. A field
    that only one side declares is skipped rather than reported as drift, the
    title is compared ignoring case and whitespace, and the authors are paired
    by ORCID before they are compared by name at all.

    Two ORCIDs are the one pair of values compared exactly. When both sides
    identify the same person by name but register different ORCIDs, one of
    the two identifiers names somebody else, and the tolerance that keeps a
    reworded name quiet would only hide it.

    The title compared is the one the technote *publishes*: ``[technote]
    title`` when the file declares one, and otherwise the title its document
    resolves from its own H1, which is the normal case and the title
    registered with the DOI. A technote whose title cannot be resolved at all
    — the document does not read, or it has no heading — is not compared on
    the title, only on its authors.
    """
    doi = parsed.technote.doi
    if doi is None:
        return []
    try:
        normalized = normalize_doi(doi)
    except ValueError:
        return []
    try:
        record = context.datacite.get_record(normalized)
    except DataCiteUnavailableError:
        return []
    if record is None:
        return []

    # Read the document only when technote.toml leaves the title to it, so a
    # titled technote's cross-check stays a single HTTP request.
    title = parsed.technote.title
    if title is None:
        title = context.document_title

    differences = _datacite_differences(parsed, record, title=title)
    if not differences:
        return []
    drift = "; ".join(differences)
    return [
        LintFinding.from_check(
            "TN105",
            f"The metadata registered for DOI {normalized} differs from the "
            f"technote: {drift}. Compare with the registered metadata at "
            f"{record.url}.",
        )
    ]


def _datacite_differences(
    parsed: TechnoteToml, record: DataCiteRecord, *, title: str | None
) -> list[str]:
    """Phrase each field where the technote and DataCite disagree.

    A side that declares nothing at all — a technote with no resolvable
    title, a record that registers no creators — is not compared on that
    field, since an absent value is not a claim that disagrees with anything.
    """
    differences: list[str] = []

    if (
        title is not None
        and record.title is not None
        and _fold(title) != _fold(record.title)
    ):
        differences.append(
            f"the registered title is '{record.title}', but the technote is "
            f"titled '{title}'"
        )

    if parsed.technote.authors and record.creators:
        differences.extend(
            _author_differences(parsed.technote.authors, record.creators)
        )

    return differences


def _author_differences(
    authors: Sequence[Person], creators: Sequence[DataCiteCreator]
) -> list[str]:
    """Phrase the ways the two author lists disagree.

    Two kinds of disagreement are reported: an author only one side has, and
    an author both sides have but under conflicting ORCIDs. Two lists that
    pair up cleanly agree about who wrote the technote however they are
    ordered and however each side spells a name, so nothing is said about
    them.
    """
    pairing = _pair_people(authors, creators)
    differences = [
        f"the ORCID registered for '{conflict.name}' is "
        f"{orcid_url(conflict.registered)}, but technote.toml declares "
        f"{orcid_url(conflict.declared)}"
        for conflict in pairing.orcid_conflicts
    ]
    clauses: list[str] = []
    if pairing.unmatched_authors:
        clauses.append(
            "technote.toml declares authors the record does not register "
            f"({_quote_names(_author_names(pairing.unmatched_authors))})"
        )
    if pairing.unmatched_creators:
        clauses.append(
            "the record registers authors technote.toml does not declare "
            f"({_quote_names(_creator_names(pairing.unmatched_creators))})"
        )
    if clauses:
        differences.append(", and ".join(clauses))
    return differences


@dataclass(frozen=True)
class _OrcidConflict:
    """One author both sides register, under two different ORCIDs."""

    name: str
    """The author's name, as technote.toml spells it."""

    declared: str
    """The ORCID technote.toml declares, normalized."""

    registered: str
    """The ORCID the DOI record registers, normalized."""


@dataclass(frozen=True)
class _AuthorPairing:
    """How a technote's declared authors pair with a DOI's creators."""

    unmatched_authors: list[Person]
    """The authors that no registered creator matched."""

    unmatched_creators: list[DataCiteCreator]
    """The registered creators that no declared author matched."""

    orcid_conflicts: list[_OrcidConflict]
    """The authors that paired by name despite conflicting ORCIDs."""


def _pair_people(
    authors: Sequence[Person], creators: Sequence[DataCiteCreator]
) -> _AuthorPairing:
    """Pair declared authors with registered creators, one to one.

    ORCIDs are paired first, wherever both sides declare one: an ORCID is the
    stronger claim about *who* an author is, so a pair it settles is settled —
    the two spellings of the name are not compared, and any difference between
    them is not reported. Whoever is left over is paired by name.

    A pair the *name* pass makes where both sides nonetheless carry an ORCID
    is a conflict: the ORCID pass searches every remaining creator, so an
    author reaching the name pass with an ORCID has already established that
    no creator registers that identifier, and a creator it then matches by
    name necessarily registers a different one. That is the strongest kind of
    claim the two sides can disagree on — one of the two ORCIDs names someone
    else — so it is reported rather than quietly paired over.

    The pairing is order-insensitive because the order DataCite lists creators
    in is not always the order technote.toml declares them in, and a legitimate
    reordering is not metadata drift worth a warning.
    """
    remaining = list(creators)
    by_name: list[Person] = []
    for author in authors:
        orcid = normalize_orcid(author.orcid)
        match = (
            None
            if orcid is None
            else next((c for c in remaining if c.orcid == orcid), None)
        )
        if match is None:
            by_name.append(author)
        else:
            remaining.remove(match)

    unmatched: list[Person] = []
    conflicts: list[_OrcidConflict] = []
    for author in by_name:
        match = next(
            (c for c in remaining if _creator_is_author(c, author)), None
        )
        if match is None:
            unmatched.append(author)
            continue
        remaining.remove(match)
        declared = normalize_orcid(author.orcid)
        if declared is not None and match.orcid is not None:
            conflicts.append(
                _OrcidConflict(
                    name=_author_name(author),
                    declared=declared,
                    registered=match.orcid,
                )
            )
    return _AuthorPairing(
        unmatched_authors=unmatched,
        unmatched_creators=remaining,
        orcid_conflicts=conflicts,
    )


def _creator_is_author(creator: DataCiteCreator, author: Person) -> bool:
    """Decide whether a registered creator names the same person as an author.

    A creator that registers no given name — every organizational creator,
    and the ``Personal`` creator with a family name alone that Rubin registers
    a committee as — is compared on that one name, against either half of the
    author's name or the whole of it. An absent given name is not drift.

    Otherwise the family names must agree, and the given names must agree
    initial-tolerantly, so a registered ``James F.`` matches a declared
    ``James`` while a registered ``John`` does not.
    """
    declared_family = _fold_name(author.name.family)
    declared_given = _fold_name(author.name.given)
    if creator.is_organizational or not creator.given_name:
        whole_name = _fold_name(creator.family_name or creator.name or "")
        return bool(whole_name) and whole_name in {
            declared_family,
            f"{declared_family} {declared_given}".strip(),
        }
    if _fold_name(creator.family_name or "") != declared_family:
        return False
    if not declared_given:
        return True
    return _given_names_agree(_fold_name(creator.given_name), declared_given)


def _given_names_agree(registered: str, declared: str) -> bool:
    """Compare two given names, tolerating initials and dropped names.

    The shorter name has to appear in the longer one, in order, with each of
    its parts either spelled out identically or standing in as an initial. So
    ``James F.`` agrees with ``James``, and ``R. Lynne`` with ``Lynne``, while
    ``John`` and ``James`` — which share no part at all — do not.
    """
    registered_parts = registered.split()
    declared_parts = declared.split()
    shorter, longer = sorted((registered_parts, declared_parts), key=len)
    matched = 0
    for part in longer:
        if matched < len(shorter) and _name_parts_agree(
            shorter[matched], part
        ):
            matched += 1
    return matched == len(shorter)


def _name_parts_agree(one: str, other: str) -> bool:
    """Compare two parts of a given name, one of which may be an initial."""
    if one == other:
        return True
    if len(one) == 1:
        return other.startswith(one)
    if len(other) == 1:
        return one.startswith(other)
    return False


def _fold_name(name: str) -> str:
    """Fold a name to the form two spellings of it compare equal in.

    Accents are decomposed and dropped, punctuation becomes whitespace, case
    is ignored, and whitespace is collapsed — so ``Ibáñez`` and ``Ibanez``
    are the same family name, and ``R. Lynne`` and ``R Lynne`` the same given
    name. Unlike the token-set comparison this replaced, the parts keep their
    order, which is what lets a transposed given and family name be seen.
    """
    decomposed = unicodedata.normalize("NFKD", name)
    depunctuated = "".join(
        " " if unicodedata.category(character).startswith("P") else character
        for character in decomposed
        if not unicodedata.combining(character)
    )
    return _fold(depunctuated)


def _author_name(author: Person) -> str:
    """Name a declared author the way a citation spells them."""
    return ", ".join(
        part for part in (author.name.family, author.name.given) if part
    )


def _author_names(authors: Sequence[Person]) -> list[str]:
    """Name each declared author the way a citation spells them."""
    return [_author_name(author) for author in authors]


def _creator_names(creators: Sequence[DataCiteCreator]) -> list[str]:
    """Name each registered creator, preferring its decomposed name parts."""
    return [creator.display_name or "unnamed" for creator in creators]


def _quote_names(names: Sequence[str]) -> str:
    """Phrase a list of names for a finding's message."""
    return ", ".join(f"'{name}'" for name in names)


def _match_author(
    results: list[AuthorSearchResult], *, orcid: str | None
) -> _AuthorSuggestion | None:
    """Pick the one author search result that confidently matches by name.

    A single result in the search's near-exact score band matches by name,
    unless it declares a *different* ORCID than the technote does, which
    proves the two are different people. Every other outcome — no results,
    several equally-good ones, a name match contradicted by an ORCID — is
    ambiguous and returns `None`.

    A declared ORCID does not select a result here: the exact ORCID lookup
    runs before this fallback, so a name-search result carrying the declared
    ORCID has already been found by identifier.
    """
    declared_orcid = normalize_orcid(orcid)
    name_matches = [
        result for result in results if result.score >= _NAME_MATCH_SCORE
    ]
    if len(name_matches) != 1:
        return None
    candidate = name_matches[0]
    candidate_orcid = normalize_orcid(candidate.orcid)
    if (
        declared_orcid is not None
        and candidate_orcid is not None
        and candidate_orcid != declared_orcid
    ):
        return None
    return _suggestion_from(candidate, basis="name")


def _suggestion_from(author: Author, *, basis: str) -> _AuthorSuggestion:
    """Build a suggestion from an author database record."""
    name = " ".join(
        part for part in (author.given_name, author.family_name) if part
    )
    return _AuthorSuggestion(
        internal_id=author.internal_id, name=name, basis=basis
    )


def _fold(text: str) -> str:
    """Case-fold text and collapse its whitespace, so that two spellings of
    the same value compare equal.
    """
    return " ".join(text.casefold().split())


def _normalize_name(name: str) -> str:
    """Fold a personal name for comparing two spellings of it."""
    return _fold(name)


@dataclass(frozen=True)
class _FormatRules:
    """How one markup format's abstract is named in a finding.

    ``directive_hint`` names the format's abstract directive, and
    ``empty_advice`` completes the TN204 message that a present directive has
    no body. Which set applies is decided by the content file's suffix, so a
    Markdown author is pointed at the fenced directive and an rST author at
    ``.. abstract::``.
    """

    directive_hint: str
    empty_advice: str


_RST_RULES = _FormatRules(
    directive_hint="'.. abstract::'",
    empty_advice="indent the abstract text under the directive.",
)
"""How a reStructuredText technote's abstract is described."""

_MYST_RULES = _FormatRules(
    directive_hint="'```{abstract}' fenced",
    empty_advice=(
        "put the abstract text between the opening and closing fences."
    ),
)
"""How a MyST Markdown or notebook technote's abstract is described."""


def check_abstract(context: LintContext) -> list[LintFinding]:
    """Check that the technote's document publishes an abstract.

    The technote is read by Sphinx (`LintContext.read_document`) and the
    resulting doctree is interrogated, so what this reports is what the
    published page carries rather than a second opinion from a parser
    Documenteer would have to keep in step with Sphinx, MyST, and the
    ``abstract`` directive. An abstract factored into an included file, or
    written in a notebook cell, is found because the *document* contains it.

    Five outcomes are distinguished (TN2xx content checks):

    - A non-empty ``abstract`` directive (rST ``.. abstract::``; MyST
      ```` ```{abstract} ```` or ``:::{abstract}``; a notebook markdown
      cell) → no findings.
    - A directive that is present but publishes nothing → a TN204 finding.
      The common cause is an abstract left unindented under
      ``.. abstract::``, which docutils reads as an empty directive. A
      directive holding only option lines counts as empty too: the
      ``abstract`` directive declares no options, so docutils parses them as
      a field list, and publishing ``:class: dropdown`` as the abstract is
      the same mistake wearing different clothes.
    - No directive but an ordinary ``Abstract`` section heading → a TN202
      finding locating the heading and pointing authors at the format's
      abstract directive.
    - None of the above → a TN201 finding: no abstract found.
    - A technote Sphinx cannot read → a TN203 finding carrying Sphinx's own
      message.

    TN202 and TN204 findings are prefixed with a ``file:line:`` location,
    which comes from the doctree and so names the file the markup is actually
    written in — an included file, where the abstract was factored into one.
    A location the doctree does not carry degrades to the file alone, and a
    notebook is located by file alone always: MyST-NB numbers a notebook's
    lines per cell, so a line number there corresponds to nothing in the
    file.

    A directory with no content file at all produces no findings here, and is
    not read: that is a structural condition, reported as TN006 by the lint
    runner.
    """
    content_path = context.content_path
    if content_path is None:
        return []

    suffix = content_path.suffix.lower()
    rules = _RST_RULES if suffix == ".rst" else _MYST_RULES

    try:
        document = context.read_document()
    except TechnoteReadError as e:
        return [
            LintFinding.from_check(
                "TN203",
                f"{content_path.name} could not be read by Sphinx: {e}",
            )
        ]

    abstracts = list(document.doctree.findall(AbstractNode))
    if any(_publishes_text(node) for node in abstracts):
        return []
    if abstracts:
        location = _locate(
            abstracts[0], context=context, fallback=content_path
        )
        return [
            LintFinding.from_check(
                "TN204",
                f"{location}the {rules.directive_hint} directive is empty — "
                f"{rules.empty_advice}",
            )
        ]

    heading = _abstract_heading(document.doctree)
    if heading is not None:
        location = _locate(heading, context=context, fallback=content_path)
        return [
            LintFinding.from_check(
                "TN202",
                f"{location}the abstract is declared as an ordinary "
                f"'Abstract' section heading. Use the "
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


def _publishes_text(node: AbstractNode) -> bool:
    """Whether an ``abstract`` directive publishes anything to read.

    A field list is not text the directive publishes as an abstract: the
    ``abstract`` directive declares no options, so docutils parses an option
    line such as ``:class: dropdown`` as directive *content* and builds a
    field list out of it. Counting that as an abstract would pass a directive
    whose published summary reads "class dropdown".
    """
    return any(
        not isinstance(child, nodes.field_list) and child.astext().strip()
        for child in node.children
    )


def _abstract_heading(doctree: nodes.document) -> nodes.title | None:
    """Find the title of a section named ``Abstract``, if the document has one.

    The ``abstract`` directive builds an `AbstractNode`, never a section, so
    a section titled "Abstract" is always an ordinary heading standing in for
    the directive.
    """
    for section in doctree.findall(nodes.section):
        title = next(iter(section.findall(nodes.title)), None)
        if title is not None and _fold(title.astext()) == "abstract":
            return title
    return None


def _locate(node: nodes.Node, *, context: LintContext, fallback: Path) -> str:
    """Format the ``file:line:`` prefix that locates a node in its source.

    The source is reported relative to the technote root when the markup
    lives inside it, and by file name otherwise — an abstract included from
    outside the technote directory still gets named. ``fallback`` names the
    file for a node the doctree records no source for at all.
    """
    source = _node_source(node)
    path = Path(source) if source is not None else fallback
    try:
        name = str(path.resolve().relative_to(context.root_dir.resolve()))
    except ValueError:
        name = path.name
    line = getattr(node, "line", None)
    if line is None or path.suffix.lower() == ".ipynb":
        # MyST-NB offsets a notebook's line numbers by cell, so a line number
        # read back from a notebook's doctree locates nothing a reader could
        # find in the file.
        return f"{name}: "
    return f"{name}:{line}: "


def _node_source(node: nodes.Node) -> str | None:
    """Find the source file a node came from, looking to its ancestors.

    docutils sets ``source`` on the nodes a parser creates, but a node a
    directive returns carries whatever the directive gave it — for the
    ``abstract`` directive, nothing. The enclosing section knows.
    """
    current: nodes.Node | None = node
    while current is not None:
        source = getattr(current, "source", None)
        if source:
            return str(source)
        current = current.parent
    return None


def check_requirements(context: LintContext) -> list[LintFinding]:
    """Statically check the technote's ``requirements.txt`` (R002/R003).

    Parses ``LintContext.requirements_text`` with
    `packaging.requirements.Requirement` and emits structural findings:

    - R002 (warning) if ``documenteer`` is absent or is declared without
      the ``[technote]`` extra — the technote build needs
      ``documenteer[technote]`` to pull in the technote theme and config.
    - R003 (warning) if ``sphinx`` is declared as its own requirement.
      ``documenteer[technote]`` already constrains Sphinx to a supported
      range, so pinning it separately risks drifting out of that window.

    A missing ``requirements.txt`` (no ``requirements_text``) is treated as
    an empty file, so ``documenteer`` is absent and R002 fires.
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
                "R002",
                "requirements.txt should declare 'documenteer[technote]' so "
                "the technote theme and Sphinx configuration are installed.",
            )
        )

    if any(canonicalize_name(req.name) == "sphinx" for req in requirements):
        findings.append(
            LintFinding.from_check(
                "R003",
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
