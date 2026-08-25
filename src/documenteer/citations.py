"""Composition of bibliographic citations for Documenteer-built sites.

Documenteer renders citations in several places — a technote's "Citing this
document" section and BibTeX copy control, a user guide's citation card and
footer — and every one of them composes the same bibliographic record. This
module is the single implementation those surfaces share: a `Citation` value
object with `~Citation.to_plain_text` and `~Citation.to_bibtex` composers, the
identifier normalizers that give every DOI, ORCID, and ROR in Documenteer the
same spelling, and the schema.org JSON-LD composer that makes a guide a
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
    "GuideCitation",
    "OrganizationAuthor",
    "PersonAuthor",
    "compose_landing_page_jsonld",
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


def _escape_latex(text: str) -> str:
    """Escape the characters LaTeX reserves, and collapse whitespace, so that
    a value can be written into a BibTeX field.

    Non-ASCII characters are left alone: BibTeX processors have read UTF-8
    for well over a decade, and rewriting names into LaTeX accent macros
    loses information that a non-LaTeX consumer of the entry wants.
    """
    return _collapse_whitespace(text).translate(_LATEX_ESCAPES)


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
        """
        family = _escape_latex(self.family_name)
        if self.given_name is None:
            return family
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
        return self.doi_url or self.url

    def to_plain_text(self) -> str:
        """Compose the citation as a plain-text bibliographic reference.

        Returns
        -------
        str
            The citation in DataCite's recommended display format:
            ``Creators (PublicationYear). Title. Publisher. Identifier``.
            Creators are separated by semicolons because a person's name
            itself contains a comma, and the identifier is the DOI URL when
            the work has a DOI and its landing page otherwise. Segments with
            no value are dropped rather than left as empty punctuation.

        Notes
        -----
        A dataset citation credited to an organization composes as::

            Vera C. Rubin Observatory (2025). Data Preview 2.
            Vera C. Rubin Observatory. https://doi.org/10.71929/rubin/2570308

        """
        byline = "; ".join(author.citation_name for author in self.authors)
        if self.date is not None:
            year = f"({self.date.year})"
            byline = f"{byline} {year}" if byline else year
        segments = [
            _collapse_whitespace(segment)
            for segment in (byline, self.title, self.publisher)
            if segment
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
        if self.authors:
            components.append(self.authors[0].key_component)
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
        """
        fields: list[tuple[str, str]] = []
        if self.authors:
            authors = " and ".join(
                author.bibtex_name for author in self.authors
            )
            fields.append(("author", authors))
        # The title is doubly braced so that BibTeX preserves its
        # capitalization instead of imposing a style's sentence case.
        fields.append(("title", f"{{{_escape_latex(self.title)}}}"))
        if self.date is not None:
            fields.append(("year", str(self.date.year)))
        if self.publisher:
            publisher_field = (
                "institution"
                if entry_type is BibtexEntryType.techreport
                else "publisher"
            )
            fields.append((publisher_field, _escape_latex(self.publisher)))
        if self.number and entry_type is BibtexEntryType.techreport:
            fields.append(("number", _escape_latex(self.number)))
        if self.doi:
            fields.append(("doi", self.doi))
        location = self.url or self.doi_url
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
            "is_self": self.is_self,
            "in_footer": self.in_footer,
            "note": self.note,
            "title": citation.title,
            "authors": [
                _author_context(author) for author in citation.authors
            ],
            "publisher": citation.publisher,
            "date": citation.date.isoformat() if citation.date else None,
            "year": citation.date.year if citation.date else None,
            "doi": citation.doi,
            "doi_url": citation.doi_url,
            "url": citation.url or citation.doi_url,
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

DATASET_LABEL = "dataset"
"""The citation label, matched case-insensitively, that types a citation as a
schema.org ``Dataset`` rather than a generic creative work."""


def _schema_type(citation: Mapping[str, Any]) -> str:
    """Choose the schema.org type that represents one citation.

    A citation labelled "Dataset" is a ``Dataset``, which is the type Google
    Dataset Search and DataCite's own crosswalk key on; the site's own
    citation is a ``WebSite``; anything else is a generic ``CreativeWork``.
    """
    label = (citation.get("label") or "").strip().casefold()
    if label == DATASET_LABEL:
        return "Dataset"
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
    citation: Mapping[str, Any], *, site_url: str | None = None
) -> dict[str, Any]:
    """Express one citation, as `GuideCitation.to_html_context` carries it, as
    a schema.org node following DataCite's crosswalk.
    """
    node: dict[str, Any] = {"@type": _schema_type(citation)}
    url = citation.get("url")
    if citation.get("is_self") and site_url:
        # The site is the DOI's landing page, so its own URL is more use to a
        # consumer than the doi.org redirect that url falls back to.
        url = site_url
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
        The serialized JSON-LD document, or `None` when there are no
        citations — a site that declares none emits no block at all.

    Notes
    -----
    The self citation is the document's own subject rather than one node among
    several: this page *is* that DOI's landing page, so a consumer reading the
    document top-level finds the DOI it came for, and the site's other
    citations hang off it as schema.org ``citation`` values. A site that
    declares citations but marks none of them ``self`` has no such subject,
    and its citations are emitted as a plain ``@graph`` instead.

    The returned string is safe to place directly in a ``<script>`` element:
    the characters that could close it early are written as JSON string
    escapes (see `_SCRIPT_ESCAPES`), so a title containing ``</script>``,
    quotes, or ampersands cannot break out of the block.
    """
    if not citations:
        return None
    nodes = [
        _citation_node(citation, site_url=site_url) for citation in citations
    ]
    self_index = next(
        (
            index
            for index, citation in enumerate(citations)
            if citation.get("is_self")
        ),
        None,
    )
    document: dict[str, Any]
    if self_index is None:
        document = {"@context": SCHEMA_ORG_CONTEXT, "@graph": nodes}
    else:
        document = {"@context": SCHEMA_ORG_CONTEXT, **nodes[self_index]}
        cited = [
            node for index, node in enumerate(nodes) if index != self_index
        ]
        if cited:
            document["citation"] = cited
    return json.dumps(
        document, ensure_ascii=False, separators=(",", ":")
    ).translate(_SCRIPT_ESCAPES)
