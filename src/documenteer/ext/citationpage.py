"""Per-page DOI landing-page metadata for a user guide's citations.

A site published with a DOI is that DOI's landing page, and every page of it
carries the site's own citation metadata. A site that publishes *several*
works, though, can register a page of its own for each — a data release's
documentation whose per-product DOIs resolve to per-product pages, say. A
``[[project.citations]]`` entry says so by setting ``page`` to the docname of
the page that is its registered landing page, optionally with the fragment
that names the work within it.

This extension is what makes such a page say so. For each page one or more
entries claim, it replaces the ``<head>`` metadata the guide's ``layout.html``
override emits:

- ``documenteer_self_citation_metatags`` becomes the claiming entry's Highwire
  and Dublin Core tags, composed against the page's own URL, so a reader
  arriving from doi.org — or saving the page to Zotero — gets the work the
  page is the landing page of rather than the site's own. Those tags are
  single-valued, so a page two entries claim emits none of them.
- ``documenteer_citations_jsonld`` becomes a block describing the claiming
  entries alone, each located at the page's own URL rather than at the doi.org
  redirect and each naming the whole it is part of — the site's own citation,
  or the site itself on a site that marks none.

A page no entry claims is left untouched, so a site that sets no ``page``
anywhere builds exactly as it did before. Nothing here composes a citation:
the entries are the ones the guide preset published into ``html_context``, and
the JSON-LD is serialized by `documenteer.citations.compose_page_jsonld`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sphinx.util import logging

from ..citations import (
    compose_highwire_tags,
    compose_page_jsonld,
    page_landing_url,
)
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

WARNING_SUBTYPE = "citation_page"
"""The ``subtype`` of every warning this extension logs.

Together with `WARNING_TYPE` this is what a site adds to Sphinx's
``suppress_warnings`` (as ``documenteer.citation_page``) to keep a claim on a
page it has not written yet from failing a ``-W`` build.
"""


def _citations(app: Sphinx) -> Sequence[dict[str, Any]]:
    """Return the site's citations, in the order they are declared.

    The guide preset publishes them into ``html_context``; a site that
    declares none publishes nothing, and this extension is then a no-op.
    """
    return app.config.html_context.get("documenteer_citations") or []


def _describe(citation: dict[str, Any]) -> str:
    """Identify one citation in a warning message, by its label when it has
    one and by its DOI otherwise.
    """
    label = citation.get("label")
    return f"{label!r}" if label else str(citation.get("doi"))


def check_citation_pages(app: Sphinx, env: BuildEnvironment) -> None:
    """Warn about a ``page`` claim naming a docname the build does not
    contain.

    The claim is the only part of the entry that is lost — its DOI still
    appears in the site's own metadata and wherever the site displays it — so
    this is a warning rather than an error, and it carries a subtype a site
    can suppress while a page is still being written.

    Parameters
    ----------
    app
        The Sphinx application.
    env
        The build environment, consulted for the docnames the project
        contains.
    """
    for citation in _citations(app):
        page = citation.get("page")
        if page is None or page in env.all_docs:
            continue
        logger.warning(
            "citation %s sets page = %r, which is not a document in this "
            "project, so no page carries that DOI's landing-page metadata. "
            "Write the value as a Sphinx docname (no file extension), "
            "optionally followed by #fragment.",
            _describe(citation),
            page,
            type=WARNING_TYPE,
            subtype=WARNING_SUBTYPE,
        )


def add_page_citations(
    app: Sphinx,
    pagename: str,
    templatename: str,
    context: dict[str, Any],
    doctree: object | None,
) -> None:
    """Replace a claimed page's citation metadata with the claiming entries'.

    This ``html-page-context`` handler runs late (see `setup`) so that the
    ``pageurl`` it builds the JSON-LD nodes' locations from is the canonical
    one the theme has already corrected. A page no entry claims returns
    early, leaving the site-wide values the guide preset published.

    Parameters
    ----------
    app
        The Sphinx application.
    pagename
        The docname of the page being rendered.
    templatename
        The template used to render the page.
    context
        The template context, modified in place.
    doctree
        The doctree for the page, or `None` for pages without a source
        document (such as ``genindex`` and ``search``). Those pages are no
        page's landing page, but they are also never claimed, so they need no
        special handling here.
    """
    citations = _citations(app)
    claiming = [
        citation for citation in citations if citation.get("page") == pagename
    ]
    if not claiming:
        return

    # The claiming entries are parts of the site's own work, and each of
    # their nodes says so by naming it. A site that marks none is still the
    # whole they are parts of, and is named by its title and base URL instead
    # -- the same WebSite node the site-wide block is about -- so the relation
    # is stated in both directions whether or not the site publishes a DOI.
    site_citation = next(
        (citation for citation in citations if citation.get("is_self")), None
    )

    # Every Highwire tag is single-valued -- one title, one DOI, one date --
    # so a page two entries claim emits none of them rather than picking a
    # winner; the JSON-LD block below is where both are stated. Only the tags
    # are replaced: ``documenteer_self_citation`` still names the citation the
    # site itself publishes, which is what the visible surfaces read.
    page_url = context.get("pageurl")
    context["documenteer_self_citation_metatags"] = (
        compose_highwire_tags(
            claiming[0],
            url=page_landing_url(claiming[0], page_url),
        )
        if len(claiming) == 1
        else None
    )
    context["documenteer_citations_jsonld"] = compose_page_jsonld(
        claiming,
        page_url=page_url,
        self_citation=site_citation,
        site_title=app.config.project or None,
        site_url=app.config.html_baseurl or None,
    )


def setup(app: Sphinx) -> ExtensionMetadata:
    """Set up the ``documenteer.ext.citationpage`` Sphinx extension."""
    app.connect("env-check-consistency", check_citation_pages)
    # Priority 600 runs the handler after the default-priority (500) handlers
    # of the theme and the extensions the guide preset loads -- notably
    # pydata-sphinx-theme's _fix_canonical_url, so that the page URL written
    # into the JSON-LD nodes is the canonical one the theme publishes.
    app.connect("html-page-context", add_page_citations, priority=600)

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
