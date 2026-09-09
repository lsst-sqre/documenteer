"""Build-time reporting of a user guide citation that states no publication
date.

A date is one of DataCite's mandatory metadata fields, and it is the field a
citation loses most quietly. Every surface that shows a citation simply omits
the segment it cannot compose: the plain text drops its ``(YYYY)``, the BibTeX
entry drops its ``year`` field, and the BibTeX key collapses to the author and
title alone. The page still renders, so nothing tells the author that the work
they publish is being cited undated.

This extension is what tells them. It reports each undated citation once per
build, as the builder is initialized, and names the place the date belongs:
the ``date`` field of the ``[[project.citations]]`` entry, and — when the
entry sources its fields from a :file:`CITATION.cff` file — the record inside
that file it reads. Which record matters, because a file whose top-level
software record is undated can carry a dated ``preferred-citation`` beside it,
and dating the wrong one would leave the citation exactly as it was.

``builder-inited`` is the event that makes "once per build" true of every
build. An undated citation is a property of the configuration alone, and a
configuration change that drops a date leaves every document up to date — so a
check run while the *environment* is checked would report nothing on the
incremental rebuild that follows the edit, which is the build the author is
watching. This event fires before any of that is decided, with the
configuration already read.

It is a warning rather than an error because a work whose date its author does
not know is still a work worth citing, and rendering is unchanged either way:
a ``-W`` site has to supply the date, and a site that accepts an undated
citation adds ``documenteer.citation_date`` to ``suppress_warnings``.

One kind of work is left out of the report altogether: software located by a
URL rather than by a DOI. Software released continuously has no publication
event to date. The year of its first release is defensible only because it
never moves, the year of its current release churns every January, and neither
says which code a reader ran — the version does, which is what such a citation
carries, qualified by the date the reader accessed it. That is how FORCE11's
software citation principles and biblatex's ``@software`` with ``urldate``
treat it, and reporting it instead would make ``suppress_warnings`` the end
state of every package site, silencing the dated works its author does want to
hear about. Two neighbours of that case are still reported: software deposited
for a DOI, because DataCite requires a publication year of every DOI and so
the date exists to be written down; and an entry reading a
:file:`CITATION.cff` file's ``preferred-citation``, because that record is a
work other than the repository the file describes, whatever its type.

Nothing here composes or alters a citation; the entries are the ones the guide
preset published into ``html_context``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sphinx.util import logging

from ..citations import CitationType, describe_citation
from ..version import __version__

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sphinx.application import Sphinx
    from sphinx.util.typing import ExtensionMetadata

__all__ = ["setup"]

logger = logging.getLogger(__name__)

WARNING_TYPE = "documenteer"
"""The ``type`` of every warning this extension logs."""

WARNING_SUBTYPE = "citation_date"
"""The ``subtype`` of every warning this extension logs.

Together with `WARNING_TYPE` this is what a site adds to Sphinx's
``suppress_warnings`` (as ``documenteer.citation_date``) to keep a knowingly
undated citation from failing a ``-W`` build.
"""

ENTRY_FIX = "Set date in its [[project.citations]] entry in documenteer.toml"
"""The fix every undated citation has, whatever it sources its fields from.

An entry's own field overrides whatever a :file:`CITATION.cff` file supplies,
so it is always an answer — and it is the only one available to a site whose
citation names a file it does not own.
"""


def _citations(app: Sphinx) -> Sequence[dict[str, Any]]:
    """Return the site's citations, in the order they are declared.

    The guide preset publishes them into ``html_context``; a site that
    declares none publishes nothing, and this extension is then a no-op.
    """
    return app.config.html_context.get("documenteer_citations") or []


def _fix(citation: dict[str, Any]) -> str:
    """Compose the sentence saying where this citation's date belongs.

    An entry that states its own fields has one place to set a date. An entry
    reading a :file:`CITATION.cff` file has two, and the second is named as
    the record the entry actually reads, spelled with the path the
    configuration wrote rather than the absolute one it resolves to.
    """
    cff = citation.get("cff")
    if not cff:
        return f"{ENTRY_FIX}."
    if citation.get("cff_preferred", True):
        record = (
            f"the preferred-citation record of {cff} (its top-level record "
            "when the file declares no preferred citation)"
        )
    else:
        record = (
            f"the top-level record of {cff}, which cff_preferred = false "
            "selects"
        )
    return f"{ENTRY_FIX}, or date-released (or year) in {record}."


def _has_no_publication_event(citation: dict[str, Any]) -> bool:
    """Report whether this citation describes a work that was never published
    on a date, which is software located by a URL rather than by a DOI.

    Two of the three conditions are the ones the module docstring reasons
    about: the work is software, and it carries no DOI whose registration
    would have fixed a publication year. The third is the record the entry
    reads. An entry citing a :file:`CITATION.cff` file's
    ``preferred-citation`` has picked out a work other than the repository
    that file describes, so it is taken at its word and reported; the
    exemption covers the entry that describes the code itself — one stating
    its own fields, or one reading a file's top-level record.

    The DOI is what the test is written against rather than the URL, because
    ``GuideCitation.to_html_context`` fills a DOI-located work's ``url`` in
    from its ``https://doi.org/`` link, leaving that field set for every
    located work.
    """
    if citation.get("type") != CitationType.software.value:
        return False
    if citation.get("doi") is not None:
        return False
    return not (citation.get("cff") and citation.get("cff_preferred", True))


def check_citation_dates(app: Sphinx) -> None:
    """Warn about each citation that states no publication date.

    Parameters
    ----------
    app
        The Sphinx application, whose ``html_context`` carries the resolved
        citations.
    """
    citations = _citations(app)
    for citation in citations:
        if citation.get("date") or _has_no_publication_event(citation):
            continue
        logger.warning(
            "citation %s states no publication date, so it is displayed "
            "without its year, its BibTeX entry carries no year field, and "
            "its BibTeX key is built without one. %s",
            # The title is the fallback for an unlabelled entry rather than
            # the key, because an undated key is one of the things this
            # warning is about: it collapses to the author and title alone,
            # so naming the entry by it would name the symptom.
            describe_citation(citation, citations, unlabelled_field="title"),
            _fix(citation),
            type=WARNING_TYPE,
            subtype=WARNING_SUBTYPE,
        )


def setup(app: Sphinx) -> ExtensionMetadata:
    """Set up the ``documenteer.ext.citationdate`` Sphinx extension."""
    app.connect("builder-inited", check_citation_dates)

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
