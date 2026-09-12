"""Composition of a technote's own citation from its technote.toml metadata.

Every technote is citable: a registered one by its DOI, and every other by
its canonical URL, which is as stable as the site that serves it. A technote
registered with a DOI is additionally that DOI's landing page, and DataCite
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
        build is reflected here, and its ``date_updated`` is the one date
        every dated surface on the page states.

    Notes
    -----
    A citation is composed for every technote, whether or not it declares a
    DOI, because a technote's URL is a citable locator in its own right. The
    DOI is what *locates* the citation when there is one — see
    `plain_text_url` — and `doi_url` is the only property that is `None`
    without one, since it is the only one that makes a claim a DOI-less
    technote cannot make.
    """

    def __init__(self, metadata: TechnoteMetadata) -> None:
        self._metadata = metadata

    @property
    def doi_url(self) -> str | None:
        """The technote's DOI as a resolvable ``https://doi.org`` URL, or
        `None` when it has no DOI.

        This is the DOI *as a DOI*, which is what the sidebar's DOI line
        displays and what only a registered technote has. The URL a rendered
        citation hyperlinks is `plain_text_url`, which falls back to the
        canonical URL.
        """
        return self._compose().doi_url

    @property
    def plain_text(self) -> str:
        """The technote's citation as a plain-text bibliographic reference.

        This is the citation DataCite asks a landing page to display:
        creators, year, title, publisher, and then the work's location — the
        DOI written as a resolvable URL, or the technote's canonical URL when
        it has no DOI.
        """
        return self._compose().to_plain_text()

    @property
    def plain_text_lead(self) -> str:
        """`plain_text` up to the location it ends in.

        A displayed citation ends in a hyperlink to the work, so the text is
        offered pre-split at that point: writing `plain_text_lead` and then a
        link to `plain_text_url` reproduces `plain_text` exactly, and a
        template never has to do string surgery to hyperlink it. The split is
        `documenteer.citations.Citation.to_plain_text_parts`, the one place
        that decides where a citation's text ends and its link begins, so
        this surface and the guide's cannot part company over it.

        A technote that has neither a DOI nor a canonical URL has nothing to
        link, and this is then the whole citation with nothing following it.
        """
        lead, _ = self._compose().to_plain_text_parts()
        return lead

    @property
    def plain_text_url(self) -> str | None:
        """The URL `plain_text` ends in and a rendered citation hyperlinks:
        the DOI as a resolvable URL, the canonical URL when the technote has
        no DOI, or `None` when it has neither.

        The name is the guide's: ``GuideCitation.to_html_context`` publishes
        the same split under ``plain_text_lead`` and ``plain_text_url``, so
        the two surfaces' templates read identically.

        `None` is what a technote that states no ``canonical_url`` and no
        ``doi`` composes. Every technote published to ``lsst.io`` states one,
        so this is the degenerate case rather than a normal one: the citation
        renders as text with no link, naming the work and its authors without
        claiming a location that was never declared.
        """
        _, location = self._compose().to_plain_text_parts()
        return location

    @property
    def bibtex(self) -> str:
        r"""The technote's BibTeX entry.

        A technote is a technical report, so the entry is a ``techreport``:
        its publisher is written as the ``institution`` and its handle
        (``SQR-000``) as the ``number``, neither of which a ``misc`` entry
        has a field for. A ``doi`` field is written only for a technote that
        has a DOI; the ``url`` field carries the canonical URL either way,
        which is how :file:`lsst.bib` already records a DOI-less technote.

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
        return self._compose().to_bibtex(
            entry_type=BibtexEntryType.techreport, key=self._metadata.id
        )

    def _compose(self) -> Citation:
        """Compose the citation from the current metadata."""
        citation_metadata = self._metadata.citation
        organization = self._metadata.organization
        canonical_url = self._metadata.canonical_url
        return Citation(
            title=self._metadata.title,
            type=CitationType.report,
            doi=(None if citation_metadata is None else citation_metadata.doi),
            authors=tuple(
                _person_author(author) for author in self._metadata.authors
            ),
            publisher=None if organization is None else organization.name,
            date=self._date,
            # A Rubin technote's DOI resolves to its Zenodo record, so the
            # technote's own site is a second landing page worth naming --
            # and the only one a technote without a DOI has.
            url=None if canonical_url is None else str(canonical_url),
            number=self._metadata.id,
        )

    @property
    def _date(self) -> PartialDate | None:
        """The date the citation is dated by.

        The metadata's ``date_updated`` is that date, whatever resolved it.
        ``technote`` reads it from technote.toml when the file declares the
        field and derives it from the committer date of the published commit
        when the file does not, so one reproducible value reaches the
        citation, the sidebar's "Updated", the page's ``<head>`` metadata,
        and the article-end citation alike — and a rebuild of an unchanged
        commit composes the same citation it composed before.

        ``date_created`` is not read: it is the day the technote was
        started, which is neither the day it was published nor the day it was
        last revised, which is why `documenteer.services.technotecff` leaves
        it out of CITATION.cff too. Metadata carrying no ``date_updated`` at
        all — which no technote ``technote`` builds has — composes an undated
        citation rather than reaching for a substitute.

        The date is formatted through the theme's own formatter, so a
        citation and the date the page displays are read the same way.
        """
        date = self._metadata.date_updated
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
