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

Both halves of a claim are checked as the environment is checked for
consistency: the docname against the documents the project contains, and the
fragment against the anchors the claimed page's doctree carries. That event is
the first moment both are available, and it is the only one — the check cannot
move to ``builder-inited``, as the undated-citation check did in #485, because
it needs doctrees, which do not exist that early. The known limitation is the
one that follows from the event: Sphinx runs ``env-check-consistency`` only
when at least one document was re-read, so an edit to
:file:`documenteer.toml` alone — which changes ``html_context``, whose
``rebuild`` is ``"html"`` — leaves every document up to date and is not
reported on that incremental rebuild. A fresh build, as in CI, reports it. The
case that matters most is unaffected: renaming a heading changes the page a
fragment names, and re-reads it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from docutils import nodes
from sphinx.util import logging

from ..citations import (
    compose_highwire_tags,
    compose_page_jsonld,
    describe_citation,
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


def _page_anchors(env: BuildEnvironment, docname: str) -> set[str]:
    """Return every anchor the claimed page publishes.

    An anchor in the rendered HTML is an ``ids`` entry on some node of the
    page's doctree, so collecting them all covers every way a page comes by
    one: a heading's generated id, an explicit ``.. _label:`` target, a
    documented object's id, a numbered figure or table. Nothing narrower does
    — ``env.tocs`` carries only each section's *first* id, which is not the
    explicit target's when a heading generated an id of its own first, and the
    std domain's labels cover explicit targets alone.

    The doctree is read from the doctree directory rather than resolved, so
    this is a read that leaves the environment's own doctree cache as it found
    it.

    Parameters
    ----------
    env
        The build environment.
    docname
        The docname of the page to read, which must be one the project
        contains.
    """
    doctree = env.get_doctree(docname)
    return {
        node_id
        for node in doctree.findall(nodes.Element)
        for node_id in node["ids"]
    }


def _explicit_anchors(env: BuildEnvironment, docname: str) -> list[str]:
    """Return the anchors of the explicit targets recorded on a page, sorted.

    These are the anchors an author *chose*, which is what makes them worth
    suggesting: the std domain records one per ``.. _label:`` target and none
    for a heading's generated id, so a suggestion built from them names
    something stable rather than a slug that moves with its heading's text.
    A page that declares no targets yields an empty list, and is then offered
    no suggestion at all.

    Parameters
    ----------
    env
        The build environment.
    docname
        The docname of the page whose targets to collect.
    """
    std: dict[str, Any] = env.domaindata.get("std", {})
    # ``labels`` holds the targets that name a section, figure, or table;
    # ``anonlabels`` holds every explicit target, including those. Both map a
    # label name to a (docname, anchor, ...) tuple, and the anchor is empty
    # for a target on the document itself, which is no location within it.
    return sorted(
        {
            target[1]
            for labels in (std.get("labels", {}), std.get("anonlabels", {}))
            for target in labels.values()
            if target[0] == docname and target[1]
        }
    )


def _did_you_mean(env: BuildEnvironment, docname: str) -> str:
    """Compose the sentence suggesting the page's explicit targets, or an
    empty string when it records none.

    Only explicit targets are offered. Listing every anchor on the page would
    name each of its headings, which is noise on a long page and, worse, an
    invitation to claim exactly the kind of generated anchor this check exists
    to catch moving.

    Parameters
    ----------
    env
        The build environment.
    docname
        The docname of the page the claim names.
    """
    anchors = _explicit_anchors(env, docname)
    if not anchors:
        return ""
    listing = ", ".join(f"#{anchor}" for anchor in anchors)
    return f" Did you mean {listing}?"


def check_citation_pages(app: Sphinx, env: BuildEnvironment) -> None:
    """Warn about a ``page`` claim naming a docname the build does not
    contain, or a fragment the claimed page does not carry.

    The claim is the only part of the entry that is lost — its DOI still
    appears in the site's own metadata and wherever the site displays it — so
    each of these is a warning rather than an error, and both carry a subtype
    a site can suppress while a page is still being written.

    A claim whose docname is wrong is reported once, for the docname: the
    fragment names a location on a page that does not exist, so there is
    nothing further to say about it.

    Parameters
    ----------
    app
        The Sphinx application.
    env
        The build environment, consulted for the docnames the project
        contains and for the anchors their doctrees carry.
    """
    # Several entries can claim one page, and each doctree is unpickled from
    # disk, so a page is read at most once however many entries name it.
    anchors: dict[str, set[str]] = {}
    citations = _citations(app)
    for citation in citations:
        page = citation.get("page")
        if page is None:
            continue
        if page not in env.all_docs:
            logger.warning(
                "citation %s sets page = %r, which is not a document in this "
                "project, so no page carries that DOI's landing-page "
                "metadata. Write the value as a Sphinx docname (no file "
                "extension), optionally followed by #fragment.",
                describe_citation(citation, citations),
                page,
                type=WARNING_TYPE,
                subtype=WARNING_SUBTYPE,
            )
            continue
        fragment = citation.get("page_fragment")
        if not fragment:
            continue
        if page not in anchors:
            anchors[page] = _page_anchors(env, page)
        if fragment in anchors[page]:
            continue
        logger.warning(
            "citation %s sets page = %r, but %r is not an anchor on %s, so "
            "the landing-page URL registered against that DOI resolves to a "
            "location the page does not contain. Add an explicit target the "
            "entry can name — .. _%s: on its own line above the heading — "
            "since a heading's own anchor is generated from its text and "
            "changes whenever the text does.%s",
            describe_citation(citation, citations),
            f"{page}#{fragment}",
            fragment,
            page,
            fragment,
            _did_you_mean(env, page),
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
