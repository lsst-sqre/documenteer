"""Composition of bibliographic citations for Documenteer-built sites.

Documenteer renders citations in several places — a technote's "Citing this
document" section and BibTeX copy control, a user guide's citation card and
footer — and every one of them composes the same bibliographic record. This
module is the single implementation those surfaces share: a `Citation` value
object with `~Citation.to_plain_text` and `~Citation.to_bibtex` composers, and
the DOI normalizer that gives every DOI in Documenteer the same spelling.

Composition is local and deterministic. Nothing here touches the network, so
the same metadata always yields byte-identical output during a Sphinx build.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

__all__ = [
    "BibtexEntryType",
    "Citation",
    "CitationAuthor",
    "OrganizationAuthor",
    "PersonAuthor",
    "doi_url",
    "normalize_doi",
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
        with a ``doi:`` prefix.

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
    These are the semantics of ``technote.sources.tomlsettings.normalize_doi``
    in the ``technote`` package, which validates a technote's ``[technote]
    doi`` field. Documenteer repeats them so that user guides and the technote
    linter — neither of which goes through technote's TOML model — normalize
    DOIs the same way a technote build does.
    """
    doi = _collapse_whitespace(value)
    for prefix in DOI_PREFIXES:
        if doi.lower().startswith(prefix):
            doi = doi[len(prefix) :]
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
        location = self.doi_url or self.url
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
