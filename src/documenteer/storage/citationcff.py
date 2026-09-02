"""Reader for a repository's CITATION.cff file.

`CITATION.cff <https://citation-file-format.github.io>`__ is the file GitHub
reads to offer a repository's "Cite this repository" button, and a project
that maintains one has already written down the bibliographic record a
Documenteer-built site wants to display. This module reads that file into the
`~documenteer.citations.Citation` value object the rest of Documenteer
composes citations from, so a guide can point at ``../CITATION.cff`` instead
of restating the same metadata in its own configuration.

Reading is the inverse of `documenteer.services.technotecff`, which generates
a technote repository's CITATION.cff from technote.toml. The two agree on the
CFF field shapes, and `tests/storage/citationcff_test.py` pins the round trip.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

from documenteer.citations import (
    Citation,
    CitationAuthor,
    CitationType,
    OrganizationAuthor,
    PersonAuthor,
)

__all__ = [
    "CitationCffError",
    "CitationCffNotFoundError",
    "CitationCffParseError",
    "read_citation_cff",
]

DOI_IDENTIFIER_TYPE = "doi"
"""The ``identifiers`` entry type that carries a DOI."""

CITATION_TYPES: dict[str, CitationType] = {
    "article": CitationType.article,
    "conference-paper": CitationType.article,
    "magazine-article": CitationType.article,
    "newspaper-article": CitationType.article,
    "data": CitationType.dataset,
    "database": CitationType.dataset,
    "dataset": CitationType.dataset,
    "report": CitationType.report,
    "software": CitationType.software,
    "software-code": CitationType.software,
    "software-container": CitationType.software,
    "software-executable": CitationType.software,
    "software-virtual-machine": CitationType.software,
}
"""The `~documenteer.citations.CitationType` each CFF ``type`` maps onto.

CFF's own vocabulary is far larger than this — its top level accepts
``software`` and ``dataset``, and a reference accepts several dozen types —
so only the ones with a counterpart are listed. A type outside this mapping
leaves the citation untyped, which publishes the same generic schema.org type
a file that declares no type at all does; guessing would be worse than saying
nothing.
"""


class CitationCffError(ValueError):
    """Base class for every failure to read a CITATION.cff file.

    A caller that only needs to report that a referenced file did not yield a
    citation — a Sphinx build reporting a configuration error, say — can catch
    this one type. Every message names the path of the offending file, so the
    message is reportable as-is.
    """


class CitationCffNotFoundError(CitationCffError):
    """Raised when there is no CITATION.cff file at the given path.

    This is kept distinct from `CitationCffParseError` because the two have
    different fixes: a missing file is usually a mistyped or wrongly-relative
    path, where an unparseable one is a problem inside a file that does
    exist.
    """


class CitationCffParseError(CitationCffError):
    """Raised when a CITATION.cff file cannot be turned into a citation.

    This covers a file that is not YAML at all, one whose YAML is not the
    mapping CFF describes, one whose ``preferred-citation`` is not a
    reference, one that names no work, and one that declares something that
    is not a DOI.
    """


def read_citation_cff(path: Path) -> Citation:
    """Read a CITATION.cff file as a citation.

    Parameters
    ----------
    path
        The path to the CITATION.cff file.

    Returns
    -------
    `~documenteer.citations.Citation`
        The citation the file describes.

    Raises
    ------
    CitationCffNotFoundError
        Raised if no file exists at ``path``.
    CitationCffParseError
        Raised if the file is not parseable as CITATION.cff, declares a
        ``preferred-citation`` that is not a reference, names no work, or
        declares something that is not a DOI.

    Notes
    -----
    When the file declares a ``preferred-citation``, *it* is the citation and
    the top-level fields are ignored entirely — no field is merged in from the
    top level. That mirrors GitHub's "Cite this repository" button, which
    renders the preferred citation alone: the top level of a CFF file
    describes the *repository* (its ``type`` may only be ``software`` or
    ``dataset``), and a project that publishes a paper, a report, or a dataset
    under its own DOI says so by adding a preferred citation. Merging the two
    would credit a work with the repository's DOI or authors whenever the
    preferred citation happened to omit one. For the same reason, a
    ``preferred-citation`` that is present but is not a mapping is an error
    rather than a fallback: quietly citing the repository stub instead would
    substitute a different work than the file asked for. A key written with
    no value at all is YAML null, and counts as absent.

    The fields read are common to CFF 1.1.0 and 1.2.0, and ``cff-version`` is
    not checked: rejecting a file whose fields are all understood buys
    nothing.
    """
    if not path.is_file():
        message = f"No CITATION.cff file at {path}."
        if not path.parent.is_dir():
            # The likeliest cause of a missing file is a path resolved from
            # the wrong directory, and a missing *parent* is the evidence for
            # that, so it is worth saying.
            message += f" Its directory, {path.parent}, does not exist either."
        raise CitationCffNotFoundError(message)
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise CitationCffParseError(
            f"Could not parse {path} as YAML: {e}"
        ) from e
    if not isinstance(document, Mapping):
        raise CitationCffParseError(
            f"{path} is not a CITATION.cff file: its content is "
            f"{type(document).__name__}, where CITATION.cff is a mapping of "
            "fields such as cff-version, title, and authors."
        )

    # A preferred-citation is a complete Reference object, so the same
    # extraction reads it and the top level alike.
    source = document.get("preferred-citation")
    if source is None:
        # No preferred citation — the repository's own fields are the
        # citation. A key written with no value at all is YAML null, and is
        # read as absent here, the way every other field of a CFF file is:
        # it holds no citation that falling back could silently drop.
        source = document
    elif not isinstance(source, Mapping):
        # Present but malformed. Falling back here would cite the repository
        # stub in place of the work the file meant to prefer, which is the
        # one substitution a reader would never notice.
        raise CitationCffParseError(
            f"{path} declares a preferred-citation that is not a mapping of "
            f"citation fields: {source!r}. Spell the preferred citation out "
            "as fields such as type, title, authors, and doi, or drop it to "
            "cite the top-level fields instead."
        )

    title = _text(source.get("title"))
    if title is None:
        raise CitationCffParseError(
            f"{path} declares no title, so there is nothing to cite. Give "
            "the file a title field."
        )
    # The authors and the date are read before the citation is constructed,
    # rather than inline below, so that the error each already raises — which
    # names the path itself — is not caught and re-wrapped by the DOI handler.
    authors = tuple(
        _author(entry, path=path) for entry in _sequence(source.get("authors"))
    )
    published = _date(source, path=path)
    try:
        return Citation(
            title=title,
            type=_citation_type(source),
            doi=_doi(source),
            authors=authors,
            publisher=_entity_name(source.get("publisher"))
            or _entity_name(source.get("institution")),
            date=published,
            url=_text(source.get("url")),
            number=_text(source.get("number")),
        )
    except ValueError as e:
        # Citation normalizes the DOI on construction, and raises a
        # ValueError that names the offending value but not the file it came
        # from. The path is what a reader needs to fix it.
        raise CitationCffParseError(f"{path} is not citable: {e}") from e


def _author(entry: Any, *, path: Path) -> CitationAuthor:
    """Compose one CFF author as a citation author.

    A CFF author is either an ``Entity`` — which is identified by its
    ``name`` — or a ``Person``, whose name is spelled across
    ``family-names``, ``given-names``, and ``name-particle``.
    """
    if not isinstance(entry, Mapping):
        raise CitationCffParseError(
            f"{path} lists an author that is not a mapping of name fields: "
            f"{entry!r}."
        )
    name = _text(entry.get("name"))
    if name is not None:
        return OrganizationAuthor(name=name)

    given_name = _text(entry.get("given-names"))
    family_name = _text(entry.get("family-names"))
    # The particle belongs with the family name in a citation, so that
    # Pieter van Dokkum is credited as "van Dokkum, Pieter" rather than
    # sorted and abbreviated under "Dokkum". `name-suffix` has no equivalent
    # home: PersonAuthor has no field that would render "Jr." correctly in
    # both plain text and BibTeX's `von Last, Jr, First` grammar, so it is
    # deliberately not carried.
    particle = _text(entry.get("name-particle"))
    if family_name is not None and particle is not None:
        family_name = f"{particle} {family_name}"
    if family_name is None:
        if given_name is None:
            raise CitationCffParseError(
                f"{path} lists an author with no name. Give every author "
                "either a name (for an organization) or family-names (for a "
                "person)."
            )
        # A mononym: the sole name is the one a citation credits.
        family_name, given_name = given_name, None

    return PersonAuthor(
        family_name=family_name,
        given_name=given_name,
        # PersonAuthor.orcid holds whatever spelling the source provides, and
        # CFF's is the https://orcid.org/ URL form.
        orcid=_text(entry.get("orcid")),
        affiliation=_text(entry.get("affiliation")),
    )


def _citation_type(source: Mapping[str, Any]) -> CitationType | None:
    """Map the record's ``type`` onto Documenteer's citation vocabulary.

    The type read is the one on whichever record is being cited: a
    ``preferred-citation``'s own type when the file declares one, and the top
    level's otherwise. The top level describes the *repository*, so its type
    would misreport the paper or report a preferred citation names.
    """
    declared = _text(source.get("type"))
    if declared is None:
        return None
    return CITATION_TYPES.get(declared.casefold())


def _doi(source: Mapping[str, Any]) -> str | None:
    """Resolve the DOI from the ``doi`` field or the ``identifiers`` array.

    CFF gives a work's DOI two homes: the dedicated ``doi`` field, and an
    ``identifiers`` entry of ``type: doi``. Zenodo's generated files use the
    latter, so both have to be read; the dedicated field wins when a file has
    both.
    """
    doi = _text(source.get("doi"))
    if doi is not None:
        return doi
    for identifier in _sequence(source.get("identifiers")):
        if (
            isinstance(identifier, Mapping)
            and _text(identifier.get("type")) == DOI_IDENTIFIER_TYPE
            and (value := _text(identifier.get("value"))) is not None
        ):
            return value
    return None


def _date(source: Mapping[str, Any], *, path: Path) -> date | None:
    """Determine the publication date.

    ``date-released`` is the field CFF's top level and Documenteer's own
    generated files use. A reference to a published work more often carries
    ``date-published``, or only a ``year`` and ``month`` — and since a
    citation displays nothing finer than the year, a bare year is worth
    honoring rather than dropping.
    """
    for field in ("date-released", "date-published"):
        value = source.get(field)
        if value is None:
            continue
        return _as_date(value, field=field, path=path)

    year = source.get("year")
    if year is None:
        return None
    try:
        return date(int(year), int(source.get("month") or 1), 1)
    except (TypeError, ValueError) as e:
        raise CitationCffParseError(
            f"{path} declares a year or month that is not a date: "
            f"year {year!r}, month {source.get('month')!r}."
        ) from e


def _as_date(value: Any, *, field: str, path: Path) -> date:
    """Read a CFF date field, which YAML may have already parsed."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value)).date()
    except ValueError as e:
        raise CitationCffParseError(
            f"{path} declares a {field} that is not a date: {value!r}."
        ) from e


def _entity_name(value: Any) -> str | None:
    """Read the name of a CFF ``Entity``, such as a publisher.

    An entity is a mapping with a ``name``; a file that writes the bare name
    instead is not valid CFF, but its intent is plain enough to honor.
    """
    if isinstance(value, Mapping):
        return _text(value.get("name"))
    return _text(value)


def _sequence(value: Any) -> list[Any]:
    """Read a CFF field that holds a list, tolerating its absence."""
    if isinstance(value, list):
        return value
    return []


def _text(value: Any) -> str | None:
    """Reduce a YAML value to non-empty text, or `None`."""
    if value is None or isinstance(value, Mapping | list):
        return None
    text = " ".join(str(value).split())
    return text or None
