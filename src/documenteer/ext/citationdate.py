"""Build-time reporting of a user guide citation that states no publication
date.

A date is one of DataCite's mandatory metadata fields, and it is the field a
citation loses most quietly. Every surface that shows a citation simply omits
the segment it cannot compose: the plain text drops its ``(YYYY)``, the BibTeX
entry drops its ``year`` field, and the BibTeX key collapses to the author and
title alone. The page still renders, so nothing tells the author that the work
they publish is being cited undated.

This extension is what tells them. It reports each undated citation once per
build, while the environment is checked, and names the place the date belongs:
the ``date`` field of the ``[[project.citations]]`` entry, and — when the
entry sources its fields from a :file:`CITATION.cff` file — the record inside
that file it reads. Which record matters, because a file whose top-level
software record is undated can carry a dated ``preferred-citation`` beside it,
and dating the wrong one would leave the citation exactly as it was.

It is a warning rather than an error because a work whose date its author does
not know is still a work worth citing, and rendering is unchanged either way:
a ``-W`` site has to supply the date, and a site that accepts an undated
citation adds ``documenteer.citation_date`` to ``suppress_warnings``. Nothing
here composes or alters a citation; the entries are the ones the guide preset
published into ``html_context``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sphinx.util import logging

from ..version import __version__

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment
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


def _describe(citation: dict[str, Any]) -> str:
    """Identify one citation in a warning message, by its label when it has
    one and by its title otherwise.

    The title is the fallback rather than the DOI because an undated entry
    need not have a DOI — a package located by its repository is the common
    case — while every entry has a title.
    """
    label = citation.get("label")
    return repr(label or citation.get("title"))


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


def check_citation_dates(app: Sphinx, env: BuildEnvironment) -> None:
    """Warn about each citation that states no publication date.

    Parameters
    ----------
    app
        The Sphinx application, whose ``html_context`` carries the resolved
        citations.
    env
        The build environment, unused: an undated citation is a property of
        the configuration, not of the documents. The parameter is part of the
        ``env-check-consistency`` signature.
    """
    for citation in _citations(app):
        if citation.get("date"):
            continue
        logger.warning(
            "citation %s states no publication date, so it is displayed "
            "without its year, its BibTeX entry carries no year field, and "
            "its BibTeX key is built without one. %s",
            _describe(citation),
            _fix(citation),
            type=WARNING_TYPE,
            subtype=WARNING_SUBTYPE,
        )


def setup(app: Sphinx) -> ExtensionMetadata:
    """Set up the ``documenteer.ext.citationdate`` Sphinx extension."""
    app.connect("env-check-consistency", check_citation_dates)

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
