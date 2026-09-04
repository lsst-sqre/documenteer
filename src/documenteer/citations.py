"""Composition of bibliographic citations for Documenteer-built sites.

Documenteer renders citations in several places — a technote's "Citing this
document" section and BibTeX copy control, a user guide's citation card and
footer — and every one of them composes the same bibliographic record. This
module is the single implementation those surfaces share: a `Citation` value
object with `~Citation.to_plain_text` and `~Citation.to_bibtex` composers, the
identifier normalizers that give every DOI, ORCID, and ROR in Documenteer the
same spelling, and the schema.org JSON-LD composers that make a guide — and,
for a site that registers a page per work, each of those pages — a
machine-readable DOI landing page.

Composition is local and deterministic. Nothing here touches the network, so
the same metadata always yields byte-identical output during a Sphinx build.
"""

from __future__ import annotations

import html
import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Any
from urllib.parse import urlparse

__all__ = [
    "BibtexEntryType",
    "Citation",
    "CitationAuthor",
    "CitationType",
    "GuideCitation",
    "OrganizationAuthor",
    "PartialDate",
    "PersonAuthor",
    "compose_highwire_tags",
    "compose_landing_page_jsonld",
    "compose_page_jsonld",
    "doi_url",
    "normalize_citation_url",
    "normalize_doi",
    "normalize_orcid",
    "orcid_url",
    "page_landing_url",
    "ror_url",
]

DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$")
"""Pattern for a bare DOI (the ``10.NNNN/suffix`` form)."""

DOI_PREFIXES = (
    "https://doi.org/",
    "http://doi.org/",
    "https://dx.doi.org/",
    "http://dx.doi.org/",
    "doi:",
)
"""Prefixes that are stripped when normalizing a DOI to its bare form."""

DOI_RESOLVER = "https://doi.org/"
"""The base URL of the DOI resolver."""

CITATION_URL_SCHEMES = ("http", "https")
"""The URL schemes a citation's landing page may be written in.

A landing page is somewhere a reader is sent and a metadata consumer
dereferences, so it has to be a URL that resolves over the web. Every other
scheme — ``ftp:``, ``mailto:``, a bare ``file:`` path — names something a
citation cannot link to.
"""

ORCID_RESOLVER = "https://orcid.org/"
"""The base URL of the ORCID resolver."""

ROR_RESOLVER = "https://ror.org/"
"""The base URL of the ROR resolver."""

SCHEMA_ORG_CONTEXT = "https://schema.org"
"""The JSON-LD ``@context`` that schema.org vocabulary is read under."""

_WHITESPACE_PATTERN = re.compile(r"\s+")

_LATEX_ESCAPES = str.maketrans(
    {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
)
"""Translation table for the characters LaTeX reserves, so that a BibTeX
field value survives being typeset."""


def _collapse_whitespace(text: str) -> str:
    """Replace any whitespace character, or group, with a single space."""
    return _WHITESPACE_PATTERN.sub(" ", text).strip()


def _clean(value: str | None) -> str | None:
    """Collapse a value's whitespace, treating a value that reduces to
    nothing — an empty or whitespace-only one — as absent.

    Collapsing *before* testing for a value is what keeps a whitespace-only
    field out of a rendered citation. Testing the raw value first would let it
    through, and it would then compose as a stray bare period or an empty
    BibTeX field.
    """
    if value is None:
        return None
    return _collapse_whitespace(value) or None


def _escape_latex(text: str) -> str:
    """Escape the characters LaTeX reserves, and collapse whitespace, so that
    a value can be written into a BibTeX field.

    Non-ASCII characters are left alone: BibTeX processors have read UTF-8
    for well over a decade, and rewriting names into LaTeX accent macros
    loses information that a non-LaTeX consumer of the entry wants.
    """
    return _collapse_whitespace(text).translate(_LATEX_ESCAPES)


def _clean_latex(value: str | None) -> str | None:
    """Escape a value for a BibTeX field, treating a value that escapes to
    nothing as absent (see `_clean`).
    """
    if value is None:
        return None
    return _escape_latex(value) or None


def _slugify(text: str) -> str:
    """Reduce text to lowercase ASCII alphanumerics, for a BibTeX key."""
    folded = (
        unicodedata.normalize("NFKD", text)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    return "".join(
        character for character in folded if character.isalnum()
    ).lower()


def _end_sentence(text: str) -> str:
    """Terminate a citation segment with a period, unless it already ends in
    sentence-final punctuation.
    """
    return text if text.endswith((".", "!", "?")) else f"{text}."


def normalize_doi(value: str) -> str:
    """Normalize a DOI into its bare form, ``10.NNNN/suffix``.

    Parameters
    ----------
    value
        A DOI, either in its bare form or expressed as a ``doi.org`` URL or
        with a ``doi:`` prefix. Whitespace around the DOI, and between a
        prefix and the DOI, is ignored.

    Returns
    -------
    str
        The bare DOI.

    Raises
    ------
    ValueError
        Raised if the value is not a syntactically-valid DOI.

    Notes
    -----
    This is a reimplementation of ``normalize_doi`` in the ``technote``
    package (``technote.metadata.doi``, also re-exported from
    ``technote.sources.tomlsettings``), which validates a technote's
    ``[technote] doi`` field. Documenteer repeats it so that user guides,
    ``documenteer technote sync-cff``, and the technote linter — none of which
    goes through technote's TOML model, and the last two of which run without
    the ``technote`` extra installed — normalize DOIs the same way a technote
    build does. ``tests/test_citations.py`` asserts the two agree whenever
    ``technote`` is installed.
    """
    doi = _collapse_whitespace(value)
    for prefix in DOI_PREFIXES:
        if doi.lower().startswith(prefix):
            doi = doi[len(prefix) :].strip()
            break
    if not DOI_PATTERN.match(doi):
        raise ValueError(
            f"Not a DOI ({value}). A DOI looks like 10.5281/zenodo.10385500, "
            "and may also be given as a https://doi.org/ URL."
        )
    return doi


def doi_url(doi: str) -> str:
    """Express a DOI as a resolvable ``https://doi.org`` URL.

    Parameters
    ----------
    doi
        A DOI in any of the spellings `normalize_doi` accepts.

    Returns
    -------
    str
        The DOI as a ``https://doi.org`` URL. DataCite's landing-page guidance
        asks that a DOI always be displayed in this resolvable form.

    Raises
    ------
    ValueError
        Raised if the value is not a syntactically-valid DOI.
    """
    return f"{DOI_RESOLVER}{normalize_doi(doi)}"


def normalize_citation_url(value: str, *, field: str = "url") -> str:
    """Normalize a citation's landing-page URL, rejecting one that could not
    be linked.

    Parameters
    ----------
    value
        The landing page, as a source wrote it. Surrounding whitespace is
        stripped.
    field
        The name of the field the value came from, so that the error names
        the field a reader has to fix. It defaults to ``url``, which is what
        both ``[[project.citations]]`` and CITATION.cff call it.

    Returns
    -------
    str
        The URL with its surrounding whitespace removed.

    Raises
    ------
    ValueError
        Raised if the value is blank, or is not an absolute ``http`` or
        ``https`` URL.

    Notes
    -----
    This is validation rather than repair, because there is no spelling to
    repair *into*: a scheme-less ``github.com/lsst/daf_butler`` could mean
    either scheme, and guessing would publish a landing page the
    configuration never stated. Left alone it is worse than rejected:
    ``Citation.location`` hands it to a template verbatim, where it becomes a
    link relative to the page being rendered and a relative IRI as a JSON-LD
    node's ``@id``.

    Blankness is checked first and separately because a blank value is the
    one that otherwise passes silently: it is truthy, so it satisfies every
    "is a URL set?" test a caller makes, and only reduces to nothing at the
    point where a citation is composed (see `_clean`) — yielding a citation
    with no location at all rather than an error.

    Each of the three ways a value can fail names *that* failure, rather than
    sharing one message: ``ftp://example.org/dp1.tar`` is a perfectly
    absolute URL, and telling its author it "is not an absolute URL" sends
    them looking for a missing scheme instead of at the scheme they wrote.
    """
    url = value.strip()
    if not url:
        raise ValueError(
            f"The citation {field} is empty. Set it to the work's landing "
            "page, as an absolute http or https URL, or drop it."
        )
    parsed = urlparse(url)
    problem: str | None = None
    if not parsed.scheme:
        problem = "is not an absolute URL"
    elif parsed.scheme not in CITATION_URL_SCHEMES:
        # Phrased around what the value starts with rather than what scheme
        # it "uses", because urlparse reads everything before the first colon
        # as a scheme: a host:port like localhost:8080 parses with scheme
        # "localhost". The prefix is re-read from the value rather than taken
        # from parsed.scheme, which urlparse has lowercased -- it is the same
        # span, and quoting it as written keeps C:\data\dp1 from being
        # reported back as "starts with c:".
        prefix = url.partition(":")[0]
        problem = f"starts with {prefix}: rather than http:// or https://"
    elif not parsed.netloc:
        problem = "names no host"
    if problem is not None:
        raise ValueError(
            f"The citation {field} ({value}) {problem}. Write the work's "
            "landing page as an http or https URL, such as "
            "https://github.com/lsst/daf_butler."
        )
    return url


def _reduce_identifier(value: str) -> str:
    """Reduce an identifier that may be written as a resolver URL to its bare
    form, the last segment of its path.
    """
    return value.strip().rstrip("/").rsplit("/", maxsplit=1)[-1]


def normalize_orcid(value: object) -> str | None:
    """Reduce an ORCID URL to its bare identifier.

    This is a lenient *reducer*, not a validator: it strips a trailing slash,
    keeps the last path segment, and uppercases the result. Ook owns the ORCID
    grammar and answers ``422`` for anything it does not recognize, so
    Documenteer deliberately does not re-implement the check here and the two
    cannot drift.

    Reducing is load-bearing rather than cosmetic. The ``technote`` package's
    ``Person.orcid`` validator re-prefixes any value that does not literally
    start with ``https://orcid``, so ``technote.toml`` yields forms such as
    ``https://orcid.org/http://orcid.org/0000-0003-3001-676X``; every one of
    them reduces to the bare identifier Ook expects. It also makes a
    comparison of two ORCIDs insensitive to the ``http``/``https`` scheme and
    to a trailing slash.

    Returns
    -------
    str or None
        The bare identifier, or `None` if ``value`` is `None`.
    """
    if value is None:
        return None
    return _reduce_identifier(str(value)).upper()


def orcid_url(value: str) -> str:
    """Express an ORCID as a resolvable ``https://orcid.org`` URL.

    Parameters
    ----------
    value
        An ORCID, either bare or written as an ``orcid.org`` URL.

    Returns
    -------
    str
        The ORCID as a ``https://orcid.org`` URL, which is the form ORCID asks
        that an identifier be displayed and linked in, and the form a
        schema.org ``Person`` node takes as its ``@id``.
    """
    return f"{ORCID_RESOLVER}{_reduce_identifier(value).upper()}"


def ror_url(value: str) -> str:
    """Express a ROR identifier as a resolvable ``https://ror.org`` URL.

    Parameters
    ----------
    value
        A ROR identifier, either bare or written as a ``ror.org`` URL.

    Returns
    -------
    str
        The identifier as a ``https://ror.org`` URL. Unlike an ORCID, a ROR
        identifier is lowercase base32 and is not case-folded.
    """
    return f"{ROR_RESOLVER}{_reduce_identifier(value)}"


@dataclass(frozen=True, kw_only=True)
class PersonAuthor:
    """A person credited as an author of a cited work."""

    family_name: str
    """The person's family name (last name in western culture)."""

    given_name: str | None = None
    """The person's given name (first name in western culture), if known."""

    orcid: str | None = None
    """The person's ORCID, in whatever spelling the source provides."""

    affiliation: str | None = None
    """The person's affiliation, as a single display name.

    Neither `Citation.to_plain_text` nor `Citation.to_bibtex` renders an
    affiliation — a bibliographic reference credits people, not their
    institutions. It is carried here because the metadata formats a citation
    is exchanged in do record it, one affiliation per creator: CFF's ``Person``
    has an ``affiliation`` string and DataCite's creators have affiliations.
    """

    @property
    def citation_name(self) -> str:
        """The name as it appears in a rendered citation, family name
        first.
        """
        if self.given_name is None:
            return self.family_name
        return f"{self.family_name}, {self.given_name}"

    @property
    def bibtex_name(self) -> str:
        """The name as a BibTeX ``author`` field entry, in BibTeX's
        ``Family, Given`` form so that a style can reorder or abbreviate it.

        A person credited by family name alone is braced instead, for the
        same reason `OrganizationAuthor.bibtex_name` is: with no comma to
        mark where the family name starts, BibTeX reads the name as given
        names followed by a family name, and a style would render Rubin's
        ``Survey Cadence Optimization Committee`` as something like "S. C. O.
        Committee". The braces say that the whole string is the name. They
        are inert around a mononym, so the branch braces every family-only
        name rather than only the multi-word ones.
        """
        family = _escape_latex(self.family_name)
        if self.given_name is None:
            return f"{{{family}}}"
        return f"{family}, {_escape_latex(self.given_name)}"

    @property
    def key_component(self) -> str:
        """The part of a BibTeX key this author contributes."""
        return _slugify(self.family_name)


@dataclass(frozen=True, kw_only=True)
class OrganizationAuthor:
    """An organization credited as an author of a cited work.

    Datasets are commonly authored by the institution that produced them
    rather than by people — Rubin's Data Preview 2 is cited to "Vera C. Rubin
    Observatory", for instance.
    """

    name: str
    """The organization's display name."""

    ror: str | None = None
    """The organization's ROR (ror.org) identifier, if known."""

    @property
    def citation_name(self) -> str:
        """The name as it appears in a rendered citation."""
        return self.name

    @property
    def bibtex_name(self) -> str:
        """The name as a BibTeX ``author`` field entry.

        The name is wrapped in braces so that BibTeX treats it as one
        corporate name rather than parsing it as a person's given and family
        names — without them, ``Vera C. Rubin Observatory`` would be
        abbreviated to something like "V. C. R. Observatory".
        """
        return f"{{{_escape_latex(self.name)}}}"

    @property
    def key_component(self) -> str:
        """The part of a BibTeX key this author contributes."""
        return _slugify(self.name)


CitationAuthor = PersonAuthor | OrganizationAuthor
"""An author of a cited work: either a person or an organization."""


class BibtexEntryType(StrEnum):
    """The BibTeX entry type to compose a citation as.

    The vocabulary is biblatex's, which is the one Zenodo and GitHub's "Cite
    this repository" export in. Classic BibTeX defined no entry type for a
    dataset or for software, and a classic style that meets one it does not
    know typesets it as ``@misc`` — which is what Documenteer emitted for
    every work before. So naming the specific type costs a reader of a classic
    style nothing and tells biblatex what the work actually is.
    """

    misc = "misc"
    """For a work without a more specific type, such as a website.

    This is the entry type DataCite's own BibTeX export uses, and the one a
    work whose type is unstated composes as.
    """

    article = "article"
    """For a paper published in a journal or conference proceedings."""

    dataset = "dataset"
    """For a published dataset."""

    software = "software"
    """For a software package or codebase."""

    techreport = "techreport"
    """For technical reports, including Rubin technotes."""


class CitationType(StrEnum):
    """The kind of work a citation describes.

    This is the citation's counterpart to DataCite's
    ``resourceTypeGeneral``: it says what the cited thing *is*, which is what
    decides the schema.org type a landing page publishes it under (see
    ``SCHEMA_ORG_TYPES``). A work whose type is unstated is not forced into one
    — an untyped citation keeps the generic default — so the vocabulary can
    stay small and every member can mean something definite.
    """

    dataset = "dataset"
    """A data release, catalog, or other published dataset.

    This is the type Google Dataset Search indexes, so it is the one worth
    setting on every data product a site publishes.
    """

    article = "article"
    """A paper published in a journal or conference proceedings."""

    software = "software"
    """A software package or codebase."""

    report = "report"
    """A technical report, including a Rubin technote."""

    other = "other"
    """A work that none of the other types describes.

    Setting it says the type was considered, where leaving the type unset
    says nothing at all; both publish the same generic schema.org type.
    """


BIBTEX_ENTRY_TYPES: dict[CitationType | None, BibtexEntryType] = {
    CitationType.dataset: BibtexEntryType.dataset,
    CitationType.article: BibtexEntryType.article,
    CitationType.software: BibtexEntryType.software,
    CitationType.report: BibtexEntryType.techreport,
    CitationType.other: BibtexEntryType.misc,
    None: BibtexEntryType.misc,
}
"""The `BibtexEntryType` each `CitationType` composes as.

The untyped case is keyed by `None` so that the mapping is total: a work that
says nothing about what it is composes as the same generic ``@misc`` a work
typed `CitationType.other` does.
"""

SCHEMA_ORG_TYPES: dict[str, str] = {
    CitationType.dataset: "Dataset",
    CitationType.article: "ScholarlyArticle",
    CitationType.software: "SoftwareSourceCode",
    CitationType.report: "Report",
    CitationType.other: "CreativeWork",
}
"""The schema.org type each `CitationType` publishes as, following DataCite's
crosswalk from ``resourceTypeGeneral`` to schema.org.
"""

_MIN_YEAR = 1000
_MAX_YEAR = 9999
"""The range a publication year is accepted in.

ISO 8601 writes a year with four digits, and a value outside that range is a
typo rather than a date.
"""

_NOT_A_DATE = (
    'Not a date ({value!r}). Write it as "2025", "2025-06", or "2025-06-30".'
)
"""The message `PartialDate.parse` rejects text with."""


@dataclass(frozen=True)
class PartialDate:
    """A publication date stated to the precision its source knows.

    A bibliographic source rarely states a full day. A ``.bib`` file, a
    journal's front matter, and a CITATION.cff reference commonly give a year
    alone, and DataCite's own mandatory metadata is a ``publicationYear``.
    Carrying such a date as a `datetime.date` would mean inventing a month and
    a day — and since Documenteer publishes the date as schema.org
    ``datePublished``, the invented day would then be asserted as fact on
    every page of a site. ISO 8601 spells reduced precision as ``YYYY`` and
    ``YYYY-MM``, schema.org ``Date`` is ISO 8601, and DataCite's crosswalk
    maps ``publicationYear`` onto ``datePublished`` as a bare year; this type
    is that spelling.

    A rendered citation shows only the year at every precision, so stating a
    date to the year costs a reader nothing: only the machine-readable
    metadata tells the three precisions apart.
    """

    year: int
    """The publication year."""

    month: int | None = None
    """The month, when the source states one."""

    day: int | None = None
    """The day, when the source states one."""

    def __post_init__(self) -> None:
        if not _MIN_YEAR <= self.year <= _MAX_YEAR:
            raise ValueError(
                f"Not a year ({self.year}). A publication year is written "
                "with four digits, as 2025."
            )
        if self.month is None:
            if self.day is not None:
                raise ValueError(
                    f"The date {self.year} states a day ({self.day}) without "
                    "a month. State a date as a year, a year and a month, or "
                    "a full date."
                )
            return
        # Composing the date is what range-checks the day against the month it
        # falls in, so that February 30 is rejected here rather than published
        # as a datePublished no calendar has. The day is composed as stated —
        # substituting a first-of-the-month for a falsy day would let a zero
        # day, which is no day at all, pass the very check it is here for.
        try:
            date(self.year, self.month, 1 if self.day is None else self.day)
        except ValueError as e:
            raise ValueError(f"Not a date ({self.isoformat()}): {e}.") from e

    @classmethod
    def from_date(cls, value: date) -> PartialDate:
        """Express a full calendar date at day precision.

        Parameters
        ----------
        value
            The date.

        Returns
        -------
        PartialDate
            The same date, stated to the day.
        """
        return cls(value.year, value.month, value.day)

    @classmethod
    def parse(cls, value: str) -> PartialDate:
        """Read a date written as ``YYYY``, ``YYYY-MM``, or ``YYYY-MM-DD``.

        Parameters
        ----------
        value
            The date, in one of the three ISO 8601 precisions.

        Returns
        -------
        PartialDate
            The date at the precision the text states.

        Raises
        ------
        ValueError
            Raised if the text is not one of the three forms, or states a
            month or a day outside its range.
        """
        parts = _collapse_whitespace(value).split("-")
        # ISO 8601 fixes the width of every component, so a two-digit year or
        # a one-digit month is a typo rather than a date to be guessed at. A
        # component must also be ASCII digits: `str.isdigit` is true of the
        # other digit forms Unicode carries, and `int` reads them, so an
        # Arabic-Indic "٢٠٢٥" would otherwise parse as a year nobody wrote.
        if (
            len(parts) > 3
            or not all(part.isascii() and part.isdigit() for part in parts)
            or len(parts[0]) != 4
            or any(len(part) != 2 for part in parts[1:])
        ):
            raise ValueError(_NOT_A_DATE.format(value=value))
        return cls(*(int(part) for part in parts))

    def isoformat(self) -> str:
        """Express the date as ISO 8601 at its own precision.

        Returns
        -------
        str
            ``YYYY``, ``YYYY-MM``, or ``YYYY-MM-DD``.
        """
        if self.month is None:
            return f"{self.year:04d}"
        if self.day is None:
            return f"{self.year:04d}-{self.month:02d}"
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"

    def __str__(self) -> str:
        return self.isoformat()

    def to_date(self) -> date | None:
        """Express the date as a `datetime.date`, when it states a full one.

        Returns
        -------
        datetime.date or None
            The calendar date, or `None` when the date is stated only to the
            year or the month — in which case there is no day to return, and
            inventing one is what this type exists to avoid.
        """
        if self.month is None or self.day is None:
            return None
        return date(self.year, self.month, self.day)


@dataclass(frozen=True, kw_only=True)
class Citation:
    """A bibliographic citation for a work, composable as plain text or
    BibTeX.

    The fields are the DataCite mandatory metadata (creators, title,
    publisher, publication year, identifier) plus the landing-page URL, which
    is the metadata a Documenteer site can supply from its own configuration
    without asking a registration agency.
    """

    title: str
    """The title of the work."""

    type: CitationType | None = None
    """The kind of work being cited.

    A citation that states its type is published under the matching
    schema.org type, which is what makes a dataset discoverable as one. The
    type is unset when nothing says what the work is, and a citation
    composes to the same plain text and BibTeX either way.
    """

    doi: str | None = None
    """The work's DOI, normalized to its bare ``10.NNNN/suffix`` form.

    A DOI given in any spelling `normalize_doi` accepts is normalized when the
    citation is constructed; a value that is not a DOI raises `ValueError`
    there rather than reaching a rendered page.
    """

    authors: tuple[CitationAuthor, ...] = ()
    """The work's authors, in the order they should be credited."""

    publisher: str | None = None
    """The organization that published the work."""

    date: PartialDate | None = None
    """The publication date, at the precision its source stated.

    Only its year appears in a rendered citation; the precision matters to the
    machine-readable metadata, which publishes the date as schema.org
    ``datePublished`` (see `PartialDate`).
    """

    url: str | None = None
    """The work's landing page, when it is not simply the DOI's target."""

    number: str | None = None
    """The work's number within its series, such as a technote's ``SQR-000``
    handle.

    This is a `BibtexEntryType.techreport` field; every other entry type has
    nowhere to put it and omits it.
    """

    def __post_init__(self) -> None:
        if self.doi is not None:
            object.__setattr__(self, "doi", normalize_doi(self.doi))

    @property
    def doi_url(self) -> str | None:
        """The DOI as a resolvable ``https://doi.org`` URL, or `None` when the
        work has no DOI.
        """
        if self.doi is None:
            return None
        return f"{DOI_RESOLVER}{self.doi}"

    @property
    def location(self) -> str | None:
        """Where the work is found: its DOI as a resolvable URL, or its
        landing page when it has no DOI, or `None` when it has neither.

        This is the identifier `to_plain_text` writes at the end of the
        citation, and the URL a rendered citation hyperlinks.
        """
        return self.doi_url or _clean(self.url)

    @property
    def _credited_authors(self) -> tuple[CitationAuthor, ...]:
        """The authors that compose to a name.

        An author whose name is blank is dropped, so that a degenerate entry
        composes as an absent author rather than as a stray separator or an
        empty BibTeX ``author`` field.
        """
        return tuple(
            author
            for author in self.authors
            if _clean(author.citation_name) is not None
        )

    def to_plain_text(self) -> str:
        """Compose the citation as a plain-text bibliographic reference.

        Returns
        -------
        str
            The citation in DataCite's recommended display format:
            ``Creators (PublicationYear). Title. Publisher. Identifier``.
            Creators are separated by semicolons because a person's name
            itself contains a comma, and the identifier is the DOI URL when
            the work has a DOI and its landing page otherwise. A segment
            with no value — including one that is only whitespace — is
            dropped rather than left as empty punctuation.

        Notes
        -----
        A dataset citation credited to an organization composes as::

            Vera C. Rubin Observatory (2025). Data Preview 2.
            Vera C. Rubin Observatory. https://doi.org/10.71929/rubin/2570308

        A surface that hyperlinks the identifier reads the same reference
        pre-split from `to_plain_text_parts` instead, rather than slicing
        this text.
        """
        lead, location = self.to_plain_text_parts()
        return lead if location is None else f"{lead}{location}"

    def to_plain_text_parts(self) -> tuple[str, str | None]:
        """Compose the citation as the two halves a linked rendering needs:
        the reference up to where the work is located, and that location
        itself.

        Returns
        -------
        lead : str
            The citation up to its trailing location, ending in the single
            space that separates the two. It is the whole reference when the
            work has no location, and empty when the citation is nothing but
            one.
        location : str or None
            Where the work is found — see `location` — or `None` when the
            citation has neither a DOI nor a landing page to name.

        Notes
        -----
        Joining the halves reproduces `to_plain_text` exactly: that method is
        written in terms of this one, so the invariant holds structurally
        rather than by two implementations agreeing.

        The split exists because a displayed citation ends in a hyperlink to
        the work, and a surface that writes the lead as text and the location
        as a link must not compose either half itself. Every such surface
        reads the split from here — the guide's footer and citation card
        through `GuideCitation.to_html_context`, and the technote's article
        footer through its ``TechnoteCitation.plain_text_lead`` — which is
        what keeps them from disagreeing about where the text ends and the
        link begins.
        """
        byline = "; ".join(
            author.citation_name for author in self._credited_authors
        )
        if self.date is not None:
            year = f"({self.date.year})"
            byline = f"{byline} {year}" if byline else year
        segments = [
            segment
            for segment in (
                _clean(byline),
                _clean(self.title),
                _clean(self.publisher),
            )
            if segment is not None
        ]
        text = " ".join(_end_sentence(segment) for segment in segments)
        location = self.location
        if location is None:
            return text, None
        return (f"{text} " if text else ""), location

    @property
    def bibtex_key(self) -> str:
        """The citation key that `to_bibtex` uses by default.

        The key is the first author, the publication year, and the first word
        of the title, each reduced to lowercase ASCII alphanumerics — for
        example ``sick2026citations``. It is derived only from the citation's
        own fields, so the same metadata always yields the same key and a
        bibliography that is regenerated on every build stays stable.
        """
        components: list[str] = []
        authors = self._credited_authors
        if authors:
            components.append(authors[0].key_component)
        if self.date is not None:
            components.append(str(self.date.year))
        components.extend(
            _slugify(word) for word in self.title.split(maxsplit=1)[:1]
        )
        key = "".join(component for component in components if component)
        return key or "citation"

    def to_bibtex(
        self,
        *,
        entry_type: BibtexEntryType | None = None,
        key: str | None = None,
    ) -> str:
        r"""Compose the citation as a BibTeX entry.

        Parameters
        ----------
        entry_type
            The BibTeX entry type, overriding the one the work's own `type`
            implies. Defaults to `None`, which composes the entry as the type
            ``BIBTEX_ENTRY_TYPES`` maps `Citation.type` onto — ``@dataset``
            for a dataset, ``@techreport`` for a report, and ``@misc`` for a
            work whose type is unstated.
        key
            The entry's citation key. Defaults to `bibtex_key`.

        Returns
        -------
        str
            The BibTeX entry, without a trailing newline. Fields appear in a
            fixed order, so regenerating the entry from unchanged metadata
            never churns a file that stores it.

        Notes
        -----
        The publisher is the ``institution`` field of a
        `BibtexEntryType.techreport` entry and the ``publisher`` field of
        every other entry type; `Citation.number` is a ``techreport`` field
        alone, and any other entry omits it. No other field varies with the
        entry type, because the model carries no field — no journal, volume,
        or version — that only one type has a home for. The ``url``
        field is the work's own landing page when it has one, falling back to
        the DOI URL; ``doi`` and ``url`` are written verbatim rather than
        LaTeX-escaped, matching what DataCite, Crossref, and Zenodo export,
        since a style's ``\url`` macro takes its argument literally.

        An optional field whose value reduces to nothing once collapsed and
        escaped is omitted, rather than written as an empty pair of braces.
        The required ``title`` field is always written, so that a blank title
        shows up as an entry to fix rather than as a silently missing field.
        """
        if entry_type is None:
            entry_type = BIBTEX_ENTRY_TYPES[self.type]
        fields: list[tuple[str, str]] = []
        credited = self._credited_authors
        if credited:
            authors = " and ".join(author.bibtex_name for author in credited)
            fields.append(("author", authors))
        # The title is doubly braced so that BibTeX preserves its
        # capitalization instead of imposing a style's sentence case. It is
        # the one required field, and is written even when it is blank.
        fields.append(("title", f"{{{_escape_latex(self.title)}}}"))
        if self.date is not None:
            fields.append(("year", str(self.date.year)))
        publisher = _clean_latex(self.publisher)
        if publisher is not None:
            publisher_field = (
                "institution"
                if entry_type is BibtexEntryType.techreport
                else "publisher"
            )
            fields.append((publisher_field, publisher))
        number = _clean_latex(self.number)
        if number is not None and entry_type is BibtexEntryType.techreport:
            fields.append(("number", number))
        if self.doi:
            fields.append(("doi", self.doi))
        location = _clean(self.url) or self.doi_url
        if location:
            fields.append(("url", location))

        body = ",\n".join(
            f"    {name} = {{{value}}}" for name, value in fields
        )
        return f"@{entry_type.value}{{{key or self.bibtex_key},\n{body}\n}}"


def _author_context(author: CitationAuthor) -> dict[str, Any]:
    """Express one author as the mapping a template or a JSON-LD block
    consumes.

    Both spellings of a person's name are carried: ``name`` is the reading
    order a schema.org ``Person`` wants, and ``citation_name`` is the
    family-name-first order a bibliographic reference is set in.
    """
    if isinstance(author, OrganizationAuthor):
        return {
            "type": "organization",
            "name": author.name,
            "citation_name": author.citation_name,
            "ror": author.ror,
        }
    name = (
        f"{author.given_name} {author.family_name}"
        if author.given_name
        else author.family_name
    )
    return {
        "type": "person",
        "name": name,
        "citation_name": author.citation_name,
        "orcid": author.orcid,
        "affiliation": author.affiliation,
    }


@dataclass(frozen=True, kw_only=True)
class GuideCitation:
    """A citation a user guide displays, together with how the guide presents
    it.

    A guide declares these in the ``[[project.citations]]`` array of
    :file:`documenteer.toml`. The bibliographic record is the `Citation`; the
    remaining fields say where and how the guide shows it, and are set in
    :file:`documenteer.toml` alone — they are never sourced from a
    CITATION.cff file.
    """

    citation: Citation
    """The bibliographic record."""

    label: str | None = None
    """A short display label distinguishing this citation from the others,
    such as "Dataset" or "Paper".
    """

    is_self: bool = False
    """Whether this is the DOI whose landing page this site is.

    At most one citation on a site is the self citation. It is the one whose
    metadata the site emits in its ``<head>``, and the subject of the
    site-wide JSON-LD block.

    This says nothing about which citation the site *asks readers to use* —
    that is `is_preferred`. The two coincide for a site that publishes its own
    DOI, and part ways for one whose preferred citation is a work published
    somewhere else, whose landing page is that publisher's.
    """

    is_preferred: bool = False
    """Whether this is the citation the site asks readers to use.

    At most one citation on a site is the preferred one. It is the entry a
    ``citation-card`` directive renders when given no label, and the one whose
    footer appearance is the default rather than opt-in.
    """

    in_footer: bool = False
    """Whether this citation appears in the site footer."""

    note: str | None = None
    """Free text about when to use this citation, displayed alongside it."""

    page: str | None = None
    """The docname of the page inside the site that is this DOI's landing
    page, or `None` when the site as a whole is.

    A site can be the landing page of one DOI, but a site that publishes
    several works can register a page of its own for each — a per-product page
    in a data release's documentation, say. That page, rather than every page
    of the site, is the one that carries this citation's machine-readable
    metadata.
    """

    page_fragment: str | None = None
    """The fragment identifier within `page` that names this work, without its
    leading ``#``, or `None` when the whole page is the landing page.

    Several works can share a page and be told apart by their fragments, which
    is why the fragment is carried separately from the docname.
    """

    cff: str | None = None
    """The path of the :file:`CITATION.cff` file the bibliographic fields came
    from, as :file:`documenteer.toml` wrote it, or `None` when the entry
    states them itself.

    This is provenance rather than presentation, and it is carried for one
    reason: a build that reports a field the citation does not state has to
    name the file the value would be set in, and the path a reader can act on
    is the relative one they wrote -- not the absolute one it resolves to.
    """

    cff_preferred: bool = True
    """Which record of `cff` supplied the fields: its ``preferred-citation``
    when true, as GitHub's "Cite this repository" button reads it, and its
    top-level record when false.

    Meaningless when `cff` is `None`; the configuration rejects setting it
    without one.
    """

    def to_html_context(self) -> dict[str, Any]:
        """Express the citation as the mapping published into Sphinx's
        ``html_context``.

        Returns
        -------
        dict
            A JSON-serializable mapping. Everything a template or a directive
            needs is precomputed here — including the ``plain_text`` and
            ``bibtex`` renderings — so that the surfaces that display a
            citation only read the context and never recompose it.

        Notes
        -----
        The mapping is the contract between this module and every guide
        surface that displays a citation: the ``<head>`` metadata, the
        ``citation-card`` directive, and the footer.

        A displayed citation ends in a hyperlink to the work, so the mapping
        carries the plain-text rendering pre-split at that location:
        ``plain_text_lead`` is the citation up to it and ``plain_text_url``
        is the location itself, and concatenating the two always reproduces
        ``plain_text``. The split comes from `Citation.to_plain_text_parts`,
        which is where that invariant lives; publishing it here is what lets
        a Jinja template render a linked citation without doing string
        surgery of its own.
        """
        citation = self.citation
        lead, location = citation.to_plain_text_parts()
        return {
            "label": self.label,
            "type": citation.type.value if citation.type else None,
            "is_self": self.is_self,
            "is_preferred": self.is_preferred,
            "in_footer": self.in_footer,
            "note": self.note,
            "page": self.page,
            "page_fragment": self.page_fragment,
            "cff": self.cff,
            "cff_preferred": self.cff_preferred,
            "title": citation.title,
            "authors": [
                _author_context(author) for author in citation.authors
            ],
            "publisher": citation.publisher,
            "date": citation.date.isoformat() if citation.date else None,
            "year": citation.date.year if citation.date else None,
            "doi": citation.doi,
            "doi_url": citation.doi_url,
            "url": _clean(citation.url) or citation.doi_url,
            "plain_text": citation.to_plain_text(),
            "plain_text_lead": lead,
            "plain_text_url": location,
            "bibtex": citation.to_bibtex(),
        }


def _meta_tag(name: str, content: str | None) -> str | None:
    """Compose one ``<meta>`` tag, or `None` when there is no value to state.

    The content is HTML-escaped with quoting on, because every value reaching
    here is author-supplied text from :file:`documenteer.toml` or a
    :file:`CITATION.cff` file: a title containing a double quote would
    otherwise close the attribute and let the rest of the title be parsed as
    markup. A value that is blank or whitespace-only is treated as absent (see
    `_clean`), so a degenerate field emits no tag rather than an empty one.
    """
    text = _clean(content)
    if text is None:
        return None
    return f'<meta name="{name}" content="{html.escape(text, quote=True)}">'


def _highwire_date(value: str | None) -> str | None:
    """Express an ISO 8601 date, at any of `PartialDate`'s three precisions,
    in one of the two forms Highwire spells a date in.

    `Google Scholar's inclusion guidelines
    <https://scholar.google.com/intl/en/scholar/inclusion.html>`__ document
    exactly two: "Provide full dates in the ``2010/5/12`` format if
    available; or a year alone otherwise." So a date stated to the day
    becomes ``YYYY/MM/DD``, and a date stated to the year stays a year rather
    than being padded with an invented month and day — the same reason
    `PartialDate` exists.

    A month-precision date has no form of its own here, so it states its
    year. ``2025/06`` is not a form the guidelines describe, and a value
    Scholar does not parse risks being ignored altogether — dropping the
    month is the lossy-but-read choice over the precise-but-unread one. The
    month is not lost to every consumer: the schema.org ``datePublished`` in
    the page's JSON-LD block still carries the full ``2025-06``, which is
    valid ISO 8601 at that precision.
    """
    text = _clean(value)
    if text is None:
        return None
    parts = text.split("-")
    if len(parts) == 3:
        return "/".join(parts)
    return parts[0]


def _author_highwire_tags(author: Mapping[str, Any]) -> list[str]:
    """Compose one author's Highwire tags: the name, then the institution and
    ORCID that qualify it.

    An author whose name is blank composes to nothing at all, rather than to
    an orphan ``citation_author_institution`` qualifying a name no tag states
    — the same rule `Citation._credited_authors` applies to a rendered
    citation.

    An organization author carries neither key, so only the ROR-bearing
    ``citation_author`` tag is emitted for it. Highwire has no tag for a ROR,
    which is why the JSON-LD block, not this one, is where an organization's
    identifier reaches a consumer.
    """
    name = _meta_tag("citation_author", author.get("citation_name"))
    if name is None:
        return []
    orcid = _clean(author.get("orcid"))
    tags = [
        name,
        _meta_tag("citation_author_institution", author.get("affiliation")),
        _meta_tag(
            "citation_author_orcid", orcid_url(orcid) if orcid else None
        ),
    ]
    return [tag for tag in tags if tag is not None]


def compose_highwire_tags(
    citation: Mapping[str, Any], *, url: str | None = None
) -> str:
    """Compose one citation as the Highwire ``<meta>`` tags a page carries in
    its ``<head>``, escaped and ready to emit.

    Parameters
    ----------
    citation
        The citation whose landing page this page is, as the mapping
        `GuideCitation.to_html_context` composes and Sphinx's ``html_context``
        publishes.
    url
        The page's own absolute URL, emitted as ``citation_fulltext_html_url``
        — the site's base URL for the site's own citation, or a claimed page's
        URL. `None` when the site declares no base URL, in which case the tag
        is omitted rather than falling back to the doi.org redirect, which is
        not where the full text is.

    Returns
    -------
    str
        The tags, one per line, in this order: ``citation_title``, then a
        ``citation_author`` per author followed by that author's
        ``citation_author_institution`` and ``citation_author_orcid``, then
        ``citation_publication_date``, ``citation_doi``,
        ``citation_publisher``, ``citation_fulltext_html_url``, and
        ``DC.identifier``. Every value is escaped with `html.escape`; a field
        the citation does not state emits no tag.

    Notes
    -----
    Highwire tags are what `Google Scholar's inclusion guidelines
    <https://scholar.google.com/intl/en/scholar/inclusion.html>`__
    specify and what Zotero's embedded-metadata translator reads, so a page
    that carries them gets a one-click "Save to Zotero" with the right title,
    creators, date, and DOI. The Dublin Core ``DC.identifier`` is emitted
    alongside them as the complement DataCite's landing-page guidance asks
    for.

    These tags are single-valued and describe the page's *landing-page
    subject*, so exactly one citation composes them: the ``self`` entry for
    the site, or the single entry that claims a page (see
    `documenteer.ext.citationpage`). A page several entries claim emits none
    of them, because there is no one work the tags could be about.

    The date is written as ``citation_publication_date``, the spelling
    Google Scholar documents and the one the ``technote`` package emits since
    0.11.0 (it wrote ``citation_date`` before). Scholar documents
    only two forms for its value — a full ``YYYY/MM/DD`` date, or a year
    alone — so a work dated to the year alone emits ``2025`` rather than an
    invented ``2025/01/01``, and a work dated to the month emits its year
    rather than a ``2025/06`` no guideline describes (see `_highwire_date`).
    """
    tags = [_meta_tag("citation_title", citation.get("title"))]
    for author in citation.get("authors", ()):
        tags.extend(_author_highwire_tags(author))
    tags.append(
        _meta_tag(
            "citation_publication_date", _highwire_date(citation.get("date"))
        )
    )
    tags.append(_meta_tag("citation_doi", citation.get("doi")))
    tags.append(_meta_tag("citation_publisher", citation.get("publisher")))
    tags.append(_meta_tag("citation_fulltext_html_url", url))
    tags.append(_meta_tag("DC.identifier", citation.get("doi_url")))
    return "\n".join(tag for tag in tags if tag is not None)


_SCRIPT_ESCAPES = {
    ord("<"): "\\u003c",
    ord(">"): "\\u003e",
    ord("&"): "\\u0026",
    0x2028: "\\u2028",
    0x2029: "\\u2029",
}
"""Characters escaped, as JSON string escapes, before a JSON-LD document is
embedded in a ``<script>`` element.

``<`` and ``>`` are the ones that matter: they are what a ``</script>`` or
``<!--`` sequence inside a title would otherwise close the element with. ``&``
is escaped too so that the same bytes are also safe as XHTML, where script
content is parsed rather than treated as raw text, and U+2028/U+2029 because a
consumer that hands the block to a JavaScript parser would read them as line
terminators.
"""


def _schema_type(citation: Mapping[str, Any]) -> str:
    """Choose the schema.org type that represents one citation.

    A citation that declares a `CitationType` is published under the matching
    schema.org type — a ``Dataset`` is what Google Dataset Search and
    DataCite's own crosswalk key on. An untyped citation says nothing about
    what the work is, so it falls back to the generic type: the site's own
    citation is a ``WebSite``, and any other work is a ``CreativeWork``.
    """
    citation_type = citation.get("type")
    if citation_type in SCHEMA_ORG_TYPES:
        return SCHEMA_ORG_TYPES[citation_type]
    return "WebSite" if citation.get("is_self") else "CreativeWork"


def _author_node(author: Mapping[str, Any]) -> dict[str, Any]:
    """Express one author, as `GuideCitation.to_html_context` carries it, as a
    schema.org ``Person`` or ``Organization`` node.
    """
    node: dict[str, Any] = {}
    if author.get("type") == "organization":
        node["@type"] = "Organization"
        if author.get("ror"):
            node["@id"] = ror_url(author["ror"])
        node["name"] = author["name"]
        return node
    node["@type"] = "Person"
    if author.get("orcid"):
        node["@id"] = orcid_url(author["orcid"])
    node["name"] = author["name"]
    if author.get("affiliation"):
        node["affiliation"] = {
            "@type": "Organization",
            "name": author["affiliation"],
        }
    return node


def _citation_node(
    citation: Mapping[str, Any], *, url_override: str | None = None
) -> dict[str, Any]:
    """Express one citation, as `GuideCitation.to_html_context` carries it, as
    a schema.org node following DataCite's crosswalk.

    ``url_override`` is the landing page the caller knows this citation to
    have — the site's own URL for the self citation, or a page's URL for a
    citation that claims one. It replaces the ``url`` the context carries,
    which falls back to the doi.org redirect and so is of less use to a
    consumer that has already arrived at the landing page.
    """
    node: dict[str, Any] = {"@type": _schema_type(citation)}
    url = url_override or citation.get("url")
    if citation.get("doi_url"):
        node["@id"] = citation["doi_url"]
        node["identifier"] = {
            "@type": "PropertyValue",
            "propertyID": "DOI",
            "value": citation["doi"],
            "url": citation["doi_url"],
        }
    elif url:
        node["@id"] = url
    node["name"] = citation["title"]
    if url:
        node["url"] = url
    authors = [_author_node(author) for author in citation.get("authors", ())]
    if authors:
        node["creator"] = authors
    if citation.get("publisher"):
        node["publisher"] = {
            "@type": "Organization",
            "name": citation["publisher"],
        }
    if citation.get("date"):
        node["datePublished"] = citation["date"]
    return node


def _minimal_reference(citation: Mapping[str, Any]) -> dict[str, Any]:
    """Express one citation as a *reference* to its node rather than as the
    node itself: its type, its identifier, and its name, and nothing else.

    A relation between two works only has to say which work it points at.
    Stating both ends in full is what would make a site-wide block grow with
    every DOI the site publishes — a data release with a DOI per data product
    would repeat the whole catalog on every page — so a relation carries this
    shape instead and a consumer follows the ``@id`` to the full record on
    the work's own landing page.
    """
    node: dict[str, Any] = {"@type": _schema_type(citation)}
    identifier = citation.get("doi_url") or citation.get("url")
    if identifier:
        node["@id"] = identifier
    node["name"] = citation["title"]
    return node


def _site_node(site_title: str | None, site_url: str | None) -> dict[str, Any]:
    """Express the site itself as a schema.org node, for a site that claims no
    DOI's landing page.

    The node carries no ``@id`` and no ``identifier``: a site that marks no
    citation ``self`` publishes no DOI of its own, and inventing an identifier
    for it would assert exactly the claim the configuration declined to make.
    A site that also declares no ``base_url`` states no ``url`` either, so the
    subject asserts only what the configuration knows.
    """
    node: dict[str, Any] = {"@type": "WebSite"}
    if site_title:
        node["name"] = site_title
    if site_url:
        node["url"] = site_url
    return node


def compose_landing_page_jsonld(
    citations: Sequence[Mapping[str, Any]],
    *,
    site_url: str | None = None,
    site_title: str | None = None,
) -> str | None:
    """Compose a site's citations as a schema.org JSON-LD document, serialized
    ready to embed in a ``<script type="application/ld+json">`` element.

    Parameters
    ----------
    citations
        The site's citations, each as the mapping
        `GuideCitation.to_html_context` composes and Sphinx's ``html_context``
        publishes.
    site_url
        The site's own base URL, used as the ``url`` of the document's
        subject — the self citation's node, or the site's own node when no
        entry is the self citation.
    site_title
        The site's own title, used as the ``name`` of the site's own node.
        Unused when an entry is the self citation, whose own title names the
        subject.

    Returns
    -------
    str or None
        The serialized JSON-LD document, or `None` when no citation belongs
        in it — a site that declares none, and one whose entries are neither
        parts nor shown in the footer, emits no block at all.

    Notes
    -----
    The self citation is the document's own subject rather than one node among
    several: this page *is* that DOI's landing page, so a consumer reading the
    document top-level finds the DOI it came for. Every other entry reaches
    the document as a *relation* of that subject, and which relation it is
    follows from whether the entry claims a landing page of its own:

    - An entry that sets `GuideCitation.page` is a **part** of the site's own
      work — a data product of a release, not something the site cites — so
      it is named in ``hasPart`` by reference alone (see
      `_minimal_reference`). Its full record belongs on the page it claims,
      which `compose_page_jsonld` composes.
    - An entry with no page is a work the site **cites**. Only the entries
      the site actually displays reach ``citation``, and in full: an entry
      that appears nowhere on the page is not something a consumer of this
      page needs the whole record of, and repeating it on all of them is
      weight every page pays for.

    An entry that is neither a part nor shown in the footer therefore appears
    in no site-wide block, though a ``citation-card`` that names it still
    renders it.

    A site that declares citations but marks none of them ``self`` — one whose
    preferred citation is a work published elsewhere, whose landing page is
    that publisher's — is still the subject of its own document. It is
    described as a ``WebSite`` carrying the site's title and URL and no
    identifier at all (see `_site_node`), and the same entries reach it under
    the same two relations, in the same shapes: a part by reference, a cited
    work in full. Only the subject differs, so the rule a consumer reads the
    block by does not depend on whether the site publishes a DOI of its own.

    The returned string is safe to place directly in a ``<script>`` element:
    the characters that could close it early are written as JSON string
    escapes (see `_SCRIPT_ESCAPES`), so a title containing ``</script>``,
    quotes, or ampersands cannot break out of the block.
    """
    self_citation = next(
        (citation for citation in citations if citation.get("is_self")), None
    )
    if self_citation is None:
        subject = _site_node(site_title, site_url)
        others = list(citations)
    else:
        # The site's own citation is the only one whose landing page is the
        # site; every other work keeps the location its own record names.
        subject = _citation_node(self_citation, url_override=site_url)
        others = [
            citation for citation in citations if citation is not self_citation
        ]

    parts = [citation for citation in others if citation.get("page")]
    cited = [
        citation
        for citation in others
        if not citation.get("page") and citation.get("in_footer")
    ]
    if self_citation is None and not parts and not cited:
        # A site with nothing to relate would publish a bare description of
        # itself, which says nothing a page's own metadata does not.
        return None

    document: dict[str, Any] = {"@context": SCHEMA_ORG_CONTEXT, **subject}
    if parts:
        document["hasPart"] = [
            _minimal_reference(citation) for citation in parts
        ]
    if cited:
        document["citation"] = [_citation_node(citation) for citation in cited]
    return _serialize_jsonld(document)


def _part_of_node(
    self_citation: Mapping[str, Any] | None,
    site_title: str | None,
    site_url: str | None,
) -> dict[str, Any] | None:
    """Build the node a claimed page's work names as the whole it is part of.

    A site that marks a citation ``self`` is that work, so the relation
    points at it by reference (see `_minimal_reference`). A site that marks
    none is still a whole its parts belong to — it is the subject of its own
    site-wide block (see `_site_node`) — so the relation points at that same
    ``WebSite`` node, which needs no DOI to be a valid target.

    Returns `None` when neither is available: a node carrying only its
    ``@type`` names no particular site, and asserting that a work is part of
    *some* website says nothing a consumer can follow.
    """
    if self_citation is not None:
        return _minimal_reference(self_citation)
    site = _site_node(site_title, site_url)
    return site if site.keys() - {"@type"} else None


def compose_page_jsonld(
    citations: Sequence[Mapping[str, Any]],
    *,
    page_url: str | None = None,
    self_citation: Mapping[str, Any] | None = None,
    site_title: str | None = None,
    site_url: str | None = None,
) -> str | None:
    """Compose the citations that claim one page as that page's own
    schema.org JSON-LD document, serialized ready to embed in a
    ``<script type="application/ld+json">`` element.

    Parameters
    ----------
    citations
        The citations whose landing page this page is — the entries whose
        `GuideCitation.page` names it — each as the mapping
        `GuideCitation.to_html_context` composes, in declaration order.
    page_url
        The page's own absolute URL, without a fragment. Each node's ``url``
        is this URL plus that citation's own fragment. `None` when the site
        declares no base URL, in which case each node keeps the location its
        record already carries (the doi.org redirect).
    self_citation
        The site's own citation, as the same kind of mapping. Each node names
        it as the work it is ``isPartOf``. `None` for a site that marks no
        citation ``self``, whose parts name the site itself instead.
    site_title
        The site's own title, and ``site_url`` its base URL. Together they
        describe the site as a ``WebSite`` node, which is what a part names
        under ``isPartOf`` on a site with no ``self`` citation. Both are
        ignored when ``self_citation`` is given, whose work is the whole
        instead.
    site_url
        See ``site_title``.

    Returns
    -------
    str or None
        The serialized JSON-LD document, or `None` when no citation claims
        the page — such a page keeps the site-wide block instead.

    Notes
    -----
    This is the per-page counterpart of `compose_landing_page_jsonld`. Where
    that one describes the site, this one describes only the works registered
    against this page, because those works' landing page is *this* page and a
    consumer arriving from doi.org must find the DOI it came for at the top of
    the document.

    A single claiming citation is the document's own subject. Several are
    emitted as a ``@graph``: they are peers on the page, told apart by their
    fragments, and subordinating one to the others would misstate the page.

    Each node also points back at the whole it is a part of, which is the
    other half of the ``hasPart`` relation `compose_landing_page_jsonld`
    states site-wide. Both ends are stated so that a consumer arriving at
    either one can reach the other, and both are stated by reference so that
    neither repeats a record the other already carries in full. The whole is
    the site's own citation where it marks one ``self``, and the site's own
    ``WebSite`` node — the subject of the site-wide block — where it marks
    none; see `_part_of_node`.
    """
    if not citations:
        return None
    part_of = _part_of_node(self_citation, site_title, site_url)
    nodes = []
    for citation in citations:
        node = _citation_node(
            citation, url_override=page_landing_url(citation, page_url)
        )
        if part_of is not None:
            # No node here can be the whole it is a part of: a citation
            # reaches this function by claiming a ``page``, and the
            # configuration rejects an entry that claims both a page and
            # ``self`` (see `CitationModel.validate_self_claims_no_page`), so
            # the site's own citation is never one of these.
            node["isPartOf"] = dict(part_of)
        nodes.append(node)
    document: dict[str, Any]
    if len(nodes) == 1:
        document = {"@context": SCHEMA_ORG_CONTEXT, **nodes[0]}
    else:
        document = {"@context": SCHEMA_ORG_CONTEXT, "@graph": nodes}
    return _serialize_jsonld(document)


def page_landing_url(
    citation: Mapping[str, Any], page_url: str | None
) -> str | None:
    """Locate a page-claiming citation on the page it claims: the page's URL
    with that citation's own fragment appended.

    Parameters
    ----------
    citation
        The claiming citation, as the mapping
        `GuideCitation.to_html_context` composes.
    page_url
        The claimed page's own absolute URL, without a fragment.

    Returns
    -------
    str or None
        The location, or `None` when the page's URL is unknown — a site that
        declares no base URL — in which case the caller states no location
        rather than inventing one.

    Notes
    -----
    The fragment is what tells two works documented on one page apart, so
    every surface that states where such a work lives — its JSON-LD node's
    ``url`` and its ``citation_fulltext_html_url`` meta tag — locates it
    through this one function and they cannot disagree.
    """
    if not page_url:
        return None
    fragment = citation.get("page_fragment")
    return f"{page_url}#{fragment}" if fragment else page_url


def _serialize_jsonld(document: Mapping[str, Any]) -> str:
    """Serialize a JSON-LD document for embedding in a ``<script>`` element.

    The characters that could close the element early are written as JSON
    string escapes (see `_SCRIPT_ESCAPES`), so the result is safe to emit
    verbatim.
    """
    return json.dumps(
        document, ensure_ascii=False, separators=(",", ":")
    ).translate(_SCRIPT_ESCAPES)
