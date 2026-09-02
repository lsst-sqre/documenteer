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

import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Any

__all__ = [
    "BibtexEntryType",
    "Citation",
    "CitationAuthor",
    "CitationType",
    "GuideCitation",
    "OrganizationAuthor",
    "PersonAuthor",
    "compose_landing_page_jsonld",
    "compose_page_jsonld",
    "doi_url",
    "normalize_doi",
    "normalize_orcid",
    "orcid_url",
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
    """The BibTeX entry type to compose a citation as."""

    misc = "misc"
    """For works without a more specific type, such as datasets and websites.

    This is the entry type DataCite's own BibTeX export uses.
    """

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

    date: date | None = None
    """The publication date. Only its year appears in a citation."""

    url: str | None = None
    """The work's landing page, when it is not simply the DOI's target."""

    number: str | None = None
    """The work's number within its series, such as a technote's ``SQR-000``
    handle.

    This is a `BibtexEntryType.techreport` field; a `BibtexEntryType.misc`
    entry has nowhere to put it and omits it.
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
            return text
        return f"{text} {location}" if text else location

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
        entry_type: BibtexEntryType = BibtexEntryType.misc,
        key: str | None = None,
    ) -> str:
        r"""Compose the citation as a BibTeX entry.

        Parameters
        ----------
        entry_type
            The BibTeX entry type. Use `BibtexEntryType.techreport` for a
            technote and `BibtexEntryType.misc`, the default, for a dataset
            or a website.
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
        The publisher is the ``publisher`` field of a
        `BibtexEntryType.misc` entry and the ``institution`` field of a
        `BibtexEntryType.techreport` one; `Citation.number` is a
        ``techreport`` field and a ``misc`` entry omits it. The ``url``
        field is the work's own landing page when it has one, falling back to
        the DOI URL; ``doi`` and ``url`` are written verbatim rather than
        LaTeX-escaped, matching what DataCite, Crossref, and Zenodo export,
        since a style's ``\url`` macro takes its argument literally.

        An optional field whose value reduces to nothing once collapsed and
        escaped is omitted, rather than written as an empty pair of braces.
        The required ``title`` field is always written, so that a blank title
        shows up as an entry to fix rather than as a silently missing field.
        """
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
    metadata the site emits in its ``<head>``, and the one a
    ``citation-card`` directive renders by default.
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
        ``plain_text``. Splitting it here is what lets a Jinja template render
        a linked citation without doing string surgery of its own, and keeps
        the card and the footer from ever disagreeing about where the text
        ends and the link begins.
        """
        citation = self.citation
        plain_text = citation.to_plain_text()
        location = citation.location
        return {
            "label": self.label,
            "type": citation.type.value if citation.type else None,
            "is_self": self.is_self,
            "in_footer": self.in_footer,
            "note": self.note,
            "page": self.page,
            "page_fragment": self.page_fragment,
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
            "plain_text": plain_text,
            "plain_text_lead": (
                plain_text[: -len(location)] if location else plain_text
            ),
            "plain_text_url": location,
            "bibtex": citation.to_bibtex(),
        }


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


def compose_landing_page_jsonld(
    citations: Sequence[Mapping[str, Any]], *, site_url: str | None = None
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
        The site's own base URL, used as the ``url`` of the self citation's
        node.

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
    renders it. A site that declares citations but marks none of them
    ``self`` has no subject to relate them to, and the same selection is
    emitted as a plain ``@graph`` instead.

    The returned string is safe to place directly in a ``<script>`` element:
    the characters that could close it early are written as JSON string
    escapes (see `_SCRIPT_ESCAPES`), so a title containing ``</script>``,
    quotes, or ampersands cannot break out of the block.
    """
    self_citation = next(
        (citation for citation in citations if citation.get("is_self")), None
    )
    if self_citation is None:
        nodes = [
            _citation_node(citation)
            for citation in citations
            if citation.get("page") or citation.get("in_footer")
        ]
        if not nodes:
            return None
        return _serialize_jsonld(
            {"@context": SCHEMA_ORG_CONTEXT, "@graph": nodes}
        )

    others = [
        citation for citation in citations if citation is not self_citation
    ]
    document: dict[str, Any] = {
        "@context": SCHEMA_ORG_CONTEXT,
        # The site's own citation is the only one whose landing page is the
        # site; every other work keeps the location its own record names.
        **_citation_node(self_citation, url_override=site_url),
    }
    parts = [citation for citation in others if citation.get("page")]
    if parts:
        document["hasPart"] = [
            _minimal_reference(citation) for citation in parts
        ]
    cited = [
        citation
        for citation in others
        if not citation.get("page") and citation.get("in_footer")
    ]
    if cited:
        document["citation"] = [_citation_node(citation) for citation in cited]
    return _serialize_jsonld(document)


def compose_page_jsonld(
    citations: Sequence[Mapping[str, Any]],
    *,
    page_url: str | None = None,
    self_citation: Mapping[str, Any] | None = None,
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
        citation ``self``, whose works are then parts of nothing it names.

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

    Each node also points back at the site's own citation as the work it is
    ``isPartOf``, which is the other half of the ``hasPart`` relation
    `compose_landing_page_jsonld` states site-wide. Both ends are stated so
    that a consumer arriving at either one can reach the other, and both are
    stated by reference (see `_minimal_reference`) so that neither repeats a
    record the other already carries in full.
    """
    if not citations:
        return None
    part_of = (
        _minimal_reference(self_citation)
        if self_citation is not None
        else None
    )
    nodes = []
    for citation in citations:
        node = _citation_node(
            citation, url_override=_page_node_url(citation, page_url)
        )
        if part_of is not None and not citation.get("is_self"):
            node["isPartOf"] = dict(part_of)
        nodes.append(node)
    document: dict[str, Any]
    if len(nodes) == 1:
        document = {"@context": SCHEMA_ORG_CONTEXT, **nodes[0]}
    else:
        document = {"@context": SCHEMA_ORG_CONTEXT, "@graph": nodes}
    return _serialize_jsonld(document)


def _page_node_url(
    citation: Mapping[str, Any], page_url: str | None
) -> str | None:
    """Build the URL of a page-claiming citation's node: the page's URL with
    that citation's own fragment appended.

    Returns `None` when the page's URL is unknown, leaving the node with the
    location its own record carries.
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
