"""Service for validating a technote's metadata and structure."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from pydantic import ValidationError
from technote.sources.tomlsettings import TechnoteToml

from documenteer.storage.authordb import AuthorDb, AuthorNotFoundError

__all__ = [
    "CHECKS",
    "Check",
    "Severity",
    "TechnoteValidationService",
    "ValidationContext",
    "ValidationFinding",
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
    resolve author identifiers. The ``technote.toml`` *text* is read eagerly;
    parsing into a `TechnoteToml` model is deferred to `parse_toml` so the
    schema-conformance check (TN001) can report a failure as a finding.
    """

    _CONTENT_FILENAMES = ("index.rst", "index.md", "index.ipynb")

    def __init__(
        self,
        *,
        root_dir: Path,
        toml_path: Path,
        toml_text: str,
        content_path: Path | None,
        requirements_path: Path | None,
        author_db: AuthorDb,
    ) -> None:
        self.root_dir = root_dir
        self.toml_path = toml_path
        self.toml_text = toml_text
        self.content_path = content_path
        self.requirements_path = requirements_path
        self.author_db = author_db

    @classmethod
    def from_dir(
        cls, root_dir: Path, author_db: AuthorDb
    ) -> ValidationContext:
        """Build a context from a technote directory."""
        toml_path = root_dir / "technote.toml"
        toml_text = toml_path.read_text()

        content_path: Path | None = None
        for filename in cls._CONTENT_FILENAMES:
            candidate = root_dir / filename
            if candidate.exists():
                content_path = candidate
                break

        requirements_path: Path | None = root_dir / "requirements.txt"
        if requirements_path is not None and not requirements_path.exists():
            requirements_path = None

        return cls(
            root_dir=root_dir,
            toml_path=toml_path,
            toml_text=toml_text,
            content_path=content_path,
            requirements_path=requirements_path,
            author_db=author_db,
        )

    def parse_toml(self) -> TechnoteToml:
        """Parse the ``technote.toml`` text into a `TechnoteToml` model.

        Raises
        ------
        pydantic.ValidationError
            If the ``technote.toml`` does not conform to the schema.
        """
        return TechnoteToml.parse_toml(self.toml_text)


class TechnoteValidationService:
    """Validate a technote's metadata, producing a list of findings."""

    def __init__(
        self, context: ValidationContext, author_db: AuthorDb
    ) -> None:
        self._context = context
        self._author_db = author_db

    def validate(self) -> list[ValidationFinding]:
        """Run the registered checks and aggregate their findings."""
        findings: list[ValidationFinding] = []

        # TN001 — schema conformance. A schema failure short-circuits the
        # remaining checks because they operate on the parsed model.
        try:
            parsed = self._context.parse_toml()
        except ValidationError as e:
            findings.append(
                ValidationFinding.from_check(
                    "TN001",
                    f"technote.toml does not conform to the schema: {e}",
                )
            )
            return findings

        findings.extend(self._check_author_internal_ids(parsed))
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
                self._author_db.get_author(author.internal_id)
            except AuthorNotFoundError:
                findings.append(
                    ValidationFinding.from_check(
                        "TN102",
                        f"Author {name} has internal_id "
                        f"'{author.internal_id}', which is not in the "
                        f"author database.",
                    )
                )
            except ValueError:
                findings.append(
                    ValidationFinding.from_check(
                        "TN103",
                        f"Could not reach the author database to verify "
                        f"internal_id '{author.internal_id}' for author "
                        f"{name}.",
                    )
                )
        return findings
