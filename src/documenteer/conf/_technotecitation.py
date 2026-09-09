"""Composition of a technote's own citation from its technote.toml metadata.

A technote registered with a DOI is that DOI's landing page, and DataCite
asks such a page to show a full bibliographic citation with the DOI written
as a resolvable link. This module turns the metadata the ``technote`` package
parses out of ``technote.toml`` into the shared
`documenteer.citations.Citation` those surfaces render, so that a technote
and a user guide compose their citations through exactly one implementation.

Composition is deferred until a value is read, because a technote's title is
not known when ``conf.py`` runs: ``technote.ext.metadata`` copies the
document's H1 into the metadata at ``html-page-context`` time when
``technote.toml`` does not state a title. Reading the metadata at render time
— the way the theme's own ``highwire_metadata_tags`` does — is what keeps the
composed citation and the rendered document in agreement.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from technote.templating.dateformat import format_iso_date

from ..citations import (
    BibtexEntryType,
    Citation,
    CitationType,
    PartialDate,
    PersonAuthor,
)

if TYPE_CHECKING:
    from datetime import datetime

    from technote.metadata.model import Person, TechnoteMetadata

__all__ = ["TechnoteCitation"]


class TechnoteCitation:
    """The citation for the technote a build is rendering.

    Parameters
    ----------
    metadata
        The technote's metadata, as ``technote`` models it. The object is
        held rather than copied: it is the same instance the theme's Jinja
        context reads, so a title filled in from the document's H1 during the
        build is reflected here.
    date_updated
        The ``date_updated`` technote.toml declares, or `None` when it
        declares none. It is passed separately because the metadata's own
        field cannot answer the question: ``technote`` stamps that one with
        the build clock whenever the file omits it, so an undeclared date is
        indistinguishable there from a real one. Read it from
        ``T.toml.technote.date_updated_datetime``, which is the declared
        value alone.

    Notes
    -----
    Every property is `None` when the technote declares no DOI, so that a
    technote without one renders no citation surface at all rather than an
    empty one.
    """

    def __init__(
        self, metadata: TechnoteMetadata, *, date_updated: datetime | None
    ) -> None:
        self._metadata = metadata
        self._date_updated = date_updated

    @property
    def doi_url(self) -> str | None:
        """The technote's DOI as a resolvable ``https://doi.org`` URL, or
        `None` when it has no DOI.
        """
        citation = self._compose()
        return None if citation is None else citation.doi_url

    @property
    def plain_text(self) -> str | None:
        """The technote's citation as a plain-text bibliographic reference,
        or `None` when it has no DOI.

        This is the citation DataCite asks a landing page to display:
        creators, year, title, publisher, and then the DOI written as a
        resolvable URL.
        """
        citation = self._compose()
        return None if citation is None else citation.to_plain_text()

    @property
    def plain_text_lead(self) -> str | None:
        """`plain_text` up to the DOI URL it ends in, or `None` when the
        technote has no DOI.

        A displayed citation ends in a hyperlink to the work, so the text is
        offered pre-split at that point: writing `plain_text_lead` and then a
        link to `doi_url` reproduces `plain_text` exactly, and a template
        never has to do string surgery to hyperlink the DOI. The split is
        `documenteer.citations.Citation.to_plain_text_parts`, the one place
        that decides where a citation's text ends and its link begins, so
        this surface and the guide's cannot part company over it.
        """
        citation = self._compose()
        if citation is None:
            return None
        lead, _ = citation.to_plain_text_parts()
        return lead

    @property
    def bibtex(self) -> str | None:
        r"""The technote's BibTeX entry, or `None` when it has no DOI.

        A technote is a technical report, so the entry is a ``techreport``:
        its publisher is written as the ``institution`` and its handle
        (``SQR-000``) as the ``number``, neither of which a ``misc`` entry
        has a field for.

        The handle is the entry's citation key as well, written verbatim, so
        the entry is keyed the way Rubin authors already cite technotes:
        lsst-texmf's :file:`lsst.bib` keys every one of its technote and
        document entries by handle, which is what ``\citeds{SQR-000}`` in an
        lsstdoc document resolves. A key composed from author, year, and
        title would agree with none of that, and it would move whenever the
        technote was retitled, re-authored, or re-dated — under a reader who
        had already stored the entry. A technote whose metadata states no
        ``id`` — one outside a series, with no handle to be keyed by — falls
        back to `documenteer.citations.Citation.bibtex_key`.
        """
        citation = self._compose()
        if citation is None:
            return None
        return citation.to_bibtex(
            entry_type=BibtexEntryType.techreport, key=self._metadata.id
        )

    @property
    def is_dated(self) -> bool:
        """Whether the citation carries a publication date.

        `documenteer.ext.citationdate` reads this to report an undated
        technote once per build, rather than looking for a missing ``(YYYY)``
        in the strings composed here.
        """
        return self._date is not None

    def _compose(self) -> Citation | None:
        """Compose the citation from the current metadata, or return `None`
        when the technote has no DOI.
        """
        doi = (
            None
            if self._metadata.citation is None
            else self._metadata.citation.doi
        )
        if doi is None:
            return None
        organization = self._metadata.organization
        canonical_url = self._metadata.canonical_url
        return Citation(
            title=self._metadata.title,
            type=CitationType.report,
            doi=doi,
            authors=tuple(
                _person_author(author) for author in self._metadata.authors
            ),
            publisher=None if organization is None else organization.name,
            date=self._date,
            # A Rubin technote's DOI resolves to its Zenodo record, so the
            # technote's own site is a second landing page worth naming.
            url=None if canonical_url is None else str(canonical_url),
            number=self._metadata.id,
        )

    @property
    def _date(self) -> PartialDate | None:
        """The date the citation is dated by, or `None` when technote.toml
        declares none.

        Only a ``date_updated`` written in technote.toml dates a citation.
        The metadata's own ``date_updated`` is deliberately not read: it is
        stamped with the build clock whenever the file omits the field, so
        reading it would date most of the fleet's citations to the day they
        were last built — and the displayed year, the BibTeX ``year``, and
        the BibTeX key would all change on every rebuild.

        ``date_created`` is not a fallback either, for the reason
        `documenteer.services.technotecff` gives for the CITATION.cff file
        this citation has to agree with: it is the day the technote was
        started, which is neither the day it was published nor the day it was
        last revised. A technote that declares no ``date_updated`` is cited
        undated, and `documenteer.ext.citationdate` says so during the build.

        The declared date is formatted through the theme's own formatter, so
        a citation and the date the page displays are read the same way.
        """
        date = self._date_updated
        return (
            None if date is None else PartialDate.parse(format_iso_date(date))
        )


def _person_author(author: Person) -> PersonAuthor:
    """Express one of the technote's authors as a citation author."""
    affiliations = [
        affiliation.name
        for affiliation in author.affiliations
        if affiliation.name
    ]
    return PersonAuthor(
        family_name=author.name.family,
        given_name=author.name.given,
        orcid=author.orcid,
        affiliation=affiliations[0] if affiliations else None,
    )
