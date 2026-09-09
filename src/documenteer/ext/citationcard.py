"""Page surfaces that display a user guide's citations: the ``citation-card``
directive and the ``doi`` role.

A site published with a DOI is that DOI's landing page, and DataCite asks a
landing page to show a full bibliographic citation with the DOI written as a
resolvable ``https://doi.org/`` link. The ``citation-card`` directive is the
block-level surface that does it: it renders one of the site's
``[[project.citations]]`` entries as a card carrying the citation, the entry's
label, and its note.

A card is a block, so a page that only needs to *mention* a work -- the first
bullet of an access list, a cell of a product table, a sentence pointing at the
paper -- cannot use one. That is the ``doi`` role: it links a declared entry's
DOI inline, from the same context the card reads, so such a mention stops being
a hand-written URL that drifts from the entry it names.

Both surfaces name an entry the same three ways: by its ``label``, by its
BibTeX key, or by its DOI in any spelling. A label is a *display* string -- it
says what the reader needs to see at the spot the citation appears -- so a site
with a registered landing page per data product writes ``label = "TAP"`` on
every one of them, and the key or the DOI is what tells those entries apart. A
selector several entries answer to is reported rather than guessed at.

The citations themselves are composed once, by the guide configuration preset,
and published into Sphinx's ``html_context`` as ``documenteer_citations`` and
``documenteer_preferred_citation``. This module only reads that context; it
never recomposes a citation, so the card, the page ``<head>`` metadata, and the
site footer can never disagree about what the site's citation says.

The card asks which citation the site wants *used*, which is
``documenteer_preferred_citation`` — not ``documenteer_self_citation``, the
narrower claim that this site is a DOI's landing page, which the ``<head>``
metadata reads. A repository whose preferred citation is a paper published
elsewhere answers the first and not the second.

This module also decides which pages reference the script behind the ``Copy
BibTeX`` buttons, for the site footer's as well as the card's (see
`CitationCopyScript`): a card is a per-page surface, so the question of which
pages carry a button is one only a per-page handler can answer.
"""

from __future__ import annotations

import difflib
from typing import TYPE_CHECKING, Any, ClassVar

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util import logging
from sphinx.util.docutils import SphinxDirective, SphinxRole
from sphinx.util.nodes import split_explicit_title

from ..citations import describe_citation, normalize_doi
from ..version import __version__

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sphinx.application import Sphinx
    from sphinx.util.typing import ExtensionMetadata
    from sphinx.writers.html5 import HTML5Translator

__all__ = [
    "CitationCard",
    "CitationCopyScript",
    "CitationDoiRole",
    "citation_bibtex",
    "setup",
]

logger = logging.getLogger(__name__)

WARNING_TYPE = "documenteer"
"""The ``type`` of every warning this extension logs."""

WARNING_SUBTYPE = "citation_card"
"""The ``subtype`` of every warning this extension logs.

Together with `WARNING_TYPE` this is what a site adds to Sphinx's
``suppress_warnings`` (as ``documenteer.citation_card``) to keep an
unresolvable card from failing a ``-W`` build.
"""

CARD_CLASS = "documenteer-citation-card"
"""The block class of the rendered card; its parts are BEM elements of it."""

NO_CITATIONS_MESSAGE = (
    "this site declares no citations, so there is nothing to render. "
    "Describe the work this site is the landing page for in a "
    "[[project.citations]] entry in documenteer.toml."
)
"""What every surface says when the site declares no citations at all.

Both surfaces say it in the same words because it is the same problem with the
same fix, and a reader who meets it from a card and from a role should not have
to work out that the two warnings mean one thing.
"""

BIBTEX_SUMMARY = "BibTeX"
"""The label of the disclosure that holds a citation's BibTeX entry."""

COPY_LABEL = "Copy BibTeX"
"""The initial label of the button that copies a BibTeX entry.

``rubin-citation-copy.js`` swaps it for a confirmation and swaps it back, and
the site footer's own button carries the same label, so the two surfaces read
identically.
"""

COPY_SCRIPT = "rubin-citation-copy.js"
"""The script that makes every copy button work.

The guide preset copies the file into ``_static/`` for a site that declares
citations; `CitationCopyScript` is what *references* it, and only from the
pages that carry a button.
"""

SELECTOR_ADVICE = (
    "An entry is selected by its label, its BibTeX key, or its DOI."
)
"""What every warning about an unresolved selector says the three ways are.

Naming all three in the warning is how an author who wrote a label that no
longer selects on its own learns that the key and the DOI do.
"""

CANDIDATE_LIMIT = 3
"""How many entries a warning names before it falls back to counting them.

A site with one registered landing page per data product declares dozens of
citations, and naming every one of them makes a warning something an author
scrolls past rather than reads. Three is enough to show what a selector looks
like without becoming the message.
"""


class citation_bibtex(nodes.General, nodes.Element):  # noqa: N801
    """A citation's BibTeX entry, shown as a copyable disclosure.

    The node carries the entry twice over: as the ``bibtex`` attribute that
    `visit_citation_bibtex_html` writes into a ``<details>`` with a copy
    button, and as a `docutils.nodes.literal_block` child that every other
    builder renders instead. A ``<details>`` and a ``<button>`` mean nothing
    in a text or LaTeX build, and emitting them there as raw HTML would put
    markup in the reader's way, so those builders fall back to the entry as a
    plain literal block.
    """


class CitationCard(SphinxDirective):
    """Render one of the site's citations as a card.

    The optional argument selects the ``[[project.citations]]`` entry to
    render, by its ``label``, its BibTeX key, or its DOI (see
    `_selects`). With no argument the directive renders the site's preferred
    citation — the work the site asks readers to cite — which is what a
    "Citing this site" page wants.

    An argument that matches no entry, an argument that matches several, and a
    site with no preferred entry, are warnings rather than errors: the
    citation metadata a site displays should never be the reason a page fails
    to build, and the warning carries a subtype so a site can suppress it
    deliberately.
    """

    has_content = False
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec: ClassVar = {
        "class": directives.class_option,
        "name": directives.unchanged,
    }

    def run(self) -> list[nodes.Node]:
        """Run the ``citation-card`` directive."""
        selector = self.arguments[0].strip() if self.arguments else None
        citation = self._select(selector)
        if citation is None:
            # Rendering nothing keeps the surrounding document valid: the
            # warning has already been logged, and leaving a system message
            # in the page would put the build's diagnostics in the published
            # site.
            return []
        return [self._build_card(citation)]

    def _citations(self) -> Sequence[dict[str, Any]]:
        """Return the site's citations, in the order they are declared."""
        return self.config.html_context.get("documenteer_citations") or []

    def _select(self, selector: str | None) -> dict[str, Any] | None:
        """Choose the citation to render, warning and returning `None` when
        no entry answers.
        """
        citations = self._citations()
        if not citations:
            self._warn(NO_CITATIONS_MESSAGE)
            return None

        if selector is None:
            preferred = self.config.html_context.get(
                "documenteer_preferred_citation"
            )
            if preferred is None:
                self._warn(
                    "no citation is marked `preferred = true`, so there is "
                    "no default entry to render. Mark the citation this site "
                    "asks readers to use with `preferred = true` in "
                    "documenteer.toml -- or with `self = true` when the site "
                    "really is that DOI's registered landing page -- or name "
                    f"an entry to render. {SELECTOR_ADVICE} "
                    f"{_describe_site(citations)}"
                )
            return preferred

        return self._resolve(selector, citations)

    def _resolve(
        self, selector: str, citations: Sequence[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """Resolve a selector to the one entry it names, warning and returning
        `None` when it names none or several.
        """
        matches = _find_citations(citations, selector)
        if not matches:
            self._warn(_unknown_selector_message(selector, citations))
            return None
        if len(matches) > 1:
            self._warn(_ambiguous_selector_message(selector, matches))
            return None
        return matches[0]

    def _build_card(self, citation: dict[str, Any]) -> nodes.Element:
        """Compose the card's node tree from one citation's context."""
        card = nodes.container(classes=[CARD_CLASS])
        card["classes"] += self.options.get("class", [])
        self.set_source_info(card)

        label = citation.get("label")
        if label:
            card += nodes.paragraph(
                "", label, classes=[f"{CARD_CLASS}__label"]
            )

        card += self._build_citation(citation)

        bibtex = citation.get("bibtex")
        if bibtex:
            card += _build_bibtex(bibtex)

        note = citation.get("note")
        if note:
            card += nodes.paragraph("", note, classes=[f"{CARD_CLASS}__note"])

        self.add_name(card)
        return card

    def _build_citation(self, citation: dict[str, Any]) -> nodes.Element:
        """Compose the citation paragraph, with its DOI as a hyperlink.

        The context carries the plain-text citation already split at its
        trailing location, so the paragraph is that lead text followed by a
        link to the location rather than a second, separately-composed
        rendering of the same record. The site footer renders the same two
        values, which is why neither surface does the splitting itself.
        """
        lead = citation.get("plain_text_lead") or ""
        url = citation.get("plain_text_url")

        paragraph = nodes.paragraph(classes=[f"{CARD_CLASS}__citation"])
        if lead:
            paragraph += nodes.Text(lead)
        if url:
            paragraph += _location_reference(url)
        return paragraph

    def _warn(self, message: str) -> None:
        """Log a warning about this directive, located at its own source."""
        _warn("citation-card", message, self.get_location())


class CitationDoiRole(SphinxRole):
    """Link one of the site's citations by its DOI, inline.

    ``:doi:`Dataset``` renders the entry labelled "Dataset" as a link to its
    DOI whose text is the resolvable ``https://doi.org/`` URL, which is how
    the Crossref and DataCite display guidelines ask a DOI to be shown. The
    standard ``text <target>`` spelling, ``:doi:`the DP2 paper <Paper>```,
    puts custom text on the same link, for the sentence that needs to read as
    prose rather than as an identifier — and is what lets a page display one
    word over an entry it selects by key or by DOI, as in
    ``:doi:`TAP <10.71929/rubin/3382540>```.

    The role always names an entry -- there is no default one -- because a
    role appears mid-sentence, where an implicit subject would be a guess at
    which of the site's works the sentence is about. The target is resolved
    against ``documenteer_citations`` through the same lookup `CitationCard`
    does, so it selects by label, by BibTeX key, or by DOI alike.

    The output is a single `docutils.nodes.reference`, so the role composes
    wherever inline markup does: prose, a list item, a table cell, a MyST
    ``{doi}`` role, and the body of a ``.. |name| replace::`` substitution
    definition. It is a link and nothing more -- no BibTeX, no note, no
    author-year text -- because those belong to the surfaces that display the
    whole record.

    Notes
    -----
    An entry that declares no DOI warns and renders unlinked text, even when
    the entry is located by a ``url``. The role's name is its contract: a
    reader who follows a ``:doi:`` link expects to arrive at a DOI, and in the
    role's default spelling the link's *text* is the DOI, so linking a
    ``https://github.com/...`` landing page under this role would display that
    URL as though it were one. Such an entry is linked with ordinary hyperlink
    syntax, or displayed with a ``citation-card``, which shows whichever
    location the entry has.
    """

    def run(self) -> tuple[list[nodes.Node], list[nodes.system_message]]:
        """Run the ``doi`` role."""
        has_title, title, selector = split_explicit_title(self.text)
        selector = selector.strip()
        citation = self._select(selector)
        doi_url = citation.get("doi_url") if citation else None
        if doi_url is None:
            # The warning has already been logged; leaving the text in place
            # keeps the sentence that holds the role readable, which a
            # missing or half-built link would not.
            return [nodes.Text(title if has_title else selector)], []
        text = title if has_title else doi_url
        return [_location_reference(doi_url, text)], []

    def _select(self, selector: str) -> dict[str, Any] | None:
        """Choose the citation to link, warning and returning `None` when no
        entry answers with a DOI.
        """
        citations = self.config.html_context.get("documenteer_citations") or []
        if not citations:
            self._warn(NO_CITATIONS_MESSAGE)
            return None

        matches = _find_citations(citations, selector)
        if not matches:
            self._warn(_unknown_selector_message(selector, citations))
            return None
        if len(matches) > 1:
            self._warn(_ambiguous_selector_message(selector, matches))
            return None
        citation = matches[0]

        if not citation.get("doi_url"):
            self._warn(_no_doi_message(citation, citations))
            return None
        return citation

    def _warn(self, message: str) -> None:
        """Log a warning about this role, located at its own source."""
        _warn("doi role", message, self.get_location())


def _location_reference(url: str, text: str | None = None) -> nodes.reference:
    """Build the external link a citation's location is displayed as, with its
    text wrapped in an inline node.

    The wrapper is what keeps the whole URL on the page. pydata-sphinx-theme
    runs a post-transform, ``ShortenLinkTransform``, that rewrites a link to
    github.com or gitlab.com into ``org/repo`` with a platform class that draws
    an octicon -- but only when the link's sole child is a bare ``Text`` equal
    to its ``refuri``, which is how it tells a URL the author left to speak for
    itself from one they gave their own words. A `docutils.nodes.inline`
    around the text takes the link out of that shape.

    A citation's location is the string a reader copies into a bibliography,
    which the Crossref and DataCite display guidelines ask to be the full
    resolvable URL, so it is displayed in full whichever host it lives on. The
    ``doi`` role builds its link here too: doi.org is not a shortened host
    today, but nothing about the role's contract depends on that staying true.
    """
    reference = nodes.reference("", "", refuri=url, internal=False)
    reference += nodes.inline("", url if text is None else text)
    return reference


def _build_bibtex(bibtex: str) -> citation_bibtex:
    """Wrap a composed BibTeX entry in its node, with the literal block that
    non-HTML builders render.

    The entry is the ``bibtex`` value of the citation's ``html_context``
    mapping, composed once by `documenteer.citations`; the card never
    recomposes it. The literal block declares the ``bibtex`` language so that
    a highlighting builder does not try to lex the entry as the site's default
    language and warn when it fails.
    """
    node = citation_bibtex()
    node["bibtex"] = bibtex
    node += nodes.literal_block(bibtex, bibtex, language="bibtex")
    return node


def visit_citation_bibtex_html(
    self: HTML5Translator, node: citation_bibtex
) -> None:
    """Write a citation's BibTeX entry as a collapsed copyable disclosure.

    The entry is offered to be copied rather than downloaded — the way GitHub,
    Zenodo, and ADS offer one — because a reader pastes it into a ``.bib``
    file they already keep. The ``<pre>`` holds the only copy of the entry, so
    ``rubin-citation-copy.js`` reads the text from it rather than from a
    duplicated ``data-`` payload that could drift from what the reader sees;
    it is also what keeps the entry selectable on a page whose script never
    runs.
    """
    self.body.append(
        f'<details class="{CARD_CLASS}__bibtex">'
        f'<summary class="{CARD_CLASS}__bibtex-summary">'
        f"{self.encode(BIBTEX_SUMMARY)}</summary>"
        f'<pre class="{CARD_CLASS}__bibtex-entry"><code>'
        f"{self.encode(node['bibtex'])}</code></pre>"
        f'<button type="button" class="{CARD_CLASS}__copy">'
        f"{self.encode(COPY_LABEL)}</button>"
        f'<span class="{CARD_CLASS}__copy-status" role="status" '
        'aria-live="polite"></span>'
        "</details>"
    )
    # The literal_block child is the fallback for the builders below; the
    # HTML surface has already written the entry into the <pre>.
    raise nodes.SkipNode


def visit_citation_bibtex_fallback(
    self: object, node: citation_bibtex
) -> None:
    """Enter the node on a builder with no disclosure to write, letting its
    literal-block child render on its own.
    """


def depart_citation_bibtex_fallback(
    self: object, node: citation_bibtex
) -> None:
    """Leave the node on a builder that rendered the literal block."""


class CitationCopyScript:
    """Reference `COPY_SCRIPT` from the pages that carry a copy button.

    A citation reaches a reader through two surfaces, and each offers the
    entry's BibTeX behind a button that copies it: the site footer, which is
    on every page, and the ``citation-card`` directive, which is on the pages
    that write one. `COPY_SCRIPT` is what wires those buttons up, so the pages
    that need it are exactly the pages that have one.

    Declaring a citation is not displaying one, which is why the question is
    asked per page rather than once for the site. An API-heavy guide names a
    citation, writes ``in_footer = false`` so a "How to cite" block does not
    repeat under several hundred generated pages, and shows the citation on a
    card on its home page: one page with a button, and the rest with none.

    Notes
    -----
    Sphinx supports adding a file to one page by calling
    `~sphinx.application.Sphinx.add_js_file` from an ``html-page-context``
    handler, which is what this does. The page's own answer is read from the
    resolved doctree Sphinx hands the handler -- the `citation_bibtex` node is
    the button -- so nothing has to be remembered in the build environment,
    and an incremental or parallel build reaches the same answer a full one
    does. ``doctree`` is `None` for a page with no source document, such as
    ``genindex`` and ``search``: those carry no card, but they do carry the
    footer, which is why the footer's answer cannot come from a doctree.

    The footer's answer is the same on every page of a build, so it is
    computed once and kept: a site with a registered landing page per data
    product declares dozens of citations, and the question would otherwise be
    re-asked of all of them for each of several hundred pages.

    Only the *reference* is added here. The file itself reaches ``_static/``
    through the guide configuration preset, which copies it for every site
    that declares a citation -- and a site that displays one has declared it,
    so a page that references the script always finds it there.
    """

    def __init__(self) -> None:
        self._footer_has_a_button: bool | None = None

    def add_copy_script(
        self,
        app: Sphinx,
        pagename: str,
        templatename: str,
        context: dict[str, Any],
        doctree: nodes.document | None,
    ) -> None:
        """Add `COPY_SCRIPT` to this page when it carries a copy button.

        Parameters
        ----------
        app
            The Sphinx application.
        pagename
            The docname of the page being rendered.
        templatename
            The template used to render the page.
        context
            The template context. Unused: the script is added through
            `~sphinx.application.Sphinx.add_js_file` rather than by editing
            the context's script list, so that Sphinx's own priority ordering
            and cache-busting apply to it.
        doctree
            The page's resolved doctree, or `None` for a page with no source
            document.
        """
        if self._footer_button(app) or _has_copy_button(doctree):
            app.add_js_file(COPY_SCRIPT)

    def _footer_button(self, app: Sphinx) -> bool:
        """Report whether the site footer offers a BibTeX entry to copy,
        computing the answer once per build.

        The footer shows every entry whose ``in_footer`` is set, and offers a
        copy button under each one that has a BibTeX entry to give -- the same
        two conditions :file:`templates/pydata/rubin-footer.html` renders the
        button under.
        """
        if self._footer_has_a_button is None:
            citations = (
                app.config.html_context.get("documenteer_citations") or []
            )
            self._footer_has_a_button = any(
                citation.get("in_footer") and citation.get("bibtex")
                for citation in citations
            )
        return self._footer_has_a_button


def _has_copy_button(doctree: nodes.document | None) -> bool:
    """Report whether a page's doctree renders a BibTeX entry to copy.

    The `citation_bibtex` node *is* the button -- `visit_citation_bibtex_html`
    writes the disclosure, the entry, and the button together -- so finding
    one is finding a button. A card whose entry has no BibTeX to give renders
    no such node, and its page gets no script, which is right: there would be
    nothing on it to wire.
    """
    if doctree is None:
        return False
    return next(doctree.findall(citation_bibtex), None) is not None


def _as_doi(selector: str) -> str | None:
    """Reduce a selector to the bare DOI it spells, or `None` when it spells
    none.

    A DOI reaches a page in whichever form its source wrote it -- bare from a
    DataCite record, ``doi:``-prefixed from a bibliography, as a
    ``https://doi.org/`` URL from a browser -- and all three name one work, so
    all three select one entry. A selector that is not a DOI at all is not an
    error here: it is a label or a key, which the caller tries in turn.
    """
    try:
        return normalize_doi(selector)
    except ValueError:
        return None


def _selects(citation: dict[str, Any], selector: str, doi: str | None) -> bool:
    """Report whether this selector names this citation.

    A selector names an entry by its ``label``, by its BibTeX key, or by its
    DOI. The first two match exactly and case-sensitively: both are short
    strings an author writes in :file:`documenteer.toml` and copies into a
    page, so a near-miss is a typo in one of the two places, and matching it
    loosely would render a citation the page did not ask for. The DOI is
    matched in its normalized form, so every spelling of one DOI selects the
    same entry.

    Parameters
    ----------
    citation
        One declared citation, as ``html_context`` publishes it.
    selector
        The text the page wrote.
    doi
        The bare DOI `selector` spells, or `None` when it spells none, passed
        in so that a selector is normalized once per lookup rather than once
        per entry.
    """
    if selector in (citation.get("label"), citation.get("bibtex_key")):
        return True
    return doi is not None and citation.get("doi") == doi


def _find_citations(
    citations: Sequence[dict[str, Any]], selector: str
) -> list[dict[str, Any]]:
    """Return every declared citation this selector names, in the order they
    are declared.

    The *set* of answers is returned rather than the first, because a label
    may repeat and a selector that names two entries names neither. Both
    surfaces resolve a selector through here, so a selector that selects a
    card always selects the same entry for a role -- and one that is ambiguous
    is ambiguous on both.
    """
    doi = _as_doi(selector)
    return [
        citation for citation in citations if _selects(citation, selector, doi)
    ]


def _unknown_selector_message(
    selector: str, citations: Sequence[dict[str, Any]]
) -> str:
    """Compose the warning for a selector no declared citation answers to.

    The warning names a handful of entries rather than all of them. Listing
    every label was already a 300-character line on a site with eleven
    citations, and a site with a registered landing page per data product
    declares dozens -- at which point the list is what an author skips rather
    than what tells them what to write. A near miss is answered with the entry
    it resembles; anything else falls back to a sample and a count.
    """
    close = _close_citations(selector, citations)
    if close:
        suggestion = (
            f"Did you mean {_describe_candidates(close)}? "
            f"{_count_citations(citations)}"
        )
    else:
        suggestion = _describe_site(citations)
    return f'no citation matches "{selector}". {SELECTOR_ADVICE} {suggestion}'


def _ambiguous_selector_message(
    selector: str, matches: Sequence[dict[str, Any]]
) -> str:
    """Compose the warning for a selector several declared citations answer
    to.

    No precedence is offered -- a label does not beat a key -- because either
    answer would silently be the wrong DOI on some page, which is exactly the
    failure this warning exists to prevent. The candidates are named by their
    BibTeX keys, since a key is unique site-wide and a label, being a display
    string, is what got the page here.
    """
    keys = ", ".join(str(match.get("bibtex_key")) for match in matches)
    return (
        f'"{selector}" matches {len(matches)} of this site\'s citations, so '
        f"it selects none of them: {keys}. A label is a display string that "
        "may repeat; name the entry you mean by its BibTeX key or its DOI."
    )


def _no_doi_message(
    citation: dict[str, Any], citations: Sequence[dict[str, Any]]
) -> str:
    """Compose the warning for an entry the ``doi`` role cannot link because
    the entry declares no DOI.

    The entry is named the way every other warning about a citation names one,
    rather than by the text the role wrote, since that text may just as well
    have been a key as a label.

    The message names the entry's ``url`` when it has one, because that is the
    link the author expected and the one they can write by hand instead.
    """
    url = citation.get("url")
    located = (
        f" It is located by url ({url}) rather than by a DOI." if url else ""
    )
    return (
        f"the citation {describe_citation(citation, citations)} declares no "
        f"DOI, so there is no DOI to link.{located} Give the entry a `doi`, "
        "or write the link with ordinary hyperlink syntax, or render the "
        "whole entry with a citation-card, which displays whichever location "
        "the entry has."
    )


def _warn(surface: str, message: str, location: Any) -> None:
    """Log one surface's warning, at the source of the markup that caused it.

    Every warning this extension logs carries the same type and subtype, so a
    site suppresses the citation surfaces' warnings as one name.
    """
    logger.warning(
        "%s: %s",
        surface,
        message,
        location=location,
        type=WARNING_TYPE,
        subtype=WARNING_SUBTYPE,
    )


def _close_citations(
    selector: str, citations: Sequence[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Return the declared citations whose label, key, or DOI most nearly
    spells this selector.

    Every string that *would* have selected an entry is a candidate for the
    near-miss search, so a mistyped key is answered as readily as a mistyped
    label. An entry matched on two of its strings at once is named once.
    """
    spellings = {
        spelling: index
        for index, citation in enumerate(citations)
        for spelling in (
            citation.get("label"),
            citation.get("bibtex_key"),
            citation.get("doi"),
        )
        if spelling
    }
    indices = sorted(
        {
            spellings[match]
            for match in difflib.get_close_matches(
                selector, list(spellings), n=CANDIDATE_LIMIT
            )
        }
    )
    return [citations[index] for index in indices]


def _describe_candidates(citations: Sequence[dict[str, Any]]) -> str:
    """Name entries in a warning, each by the key that selects it and the
    label a reader recognizes it by.

    The key leads because it is what the author has to write to select the
    entry unambiguously; the label follows because it is what they will
    recognize from :file:`documenteer.toml`.
    """
    return ", ".join(
        f"{citation.get('bibtex_key')} ({citation['label']})"
        if citation.get("label")
        else str(citation.get("bibtex_key"))
        for citation in citations
    )


def _count_citations(citations: Sequence[dict[str, Any]]) -> str:
    """State how many citations the site declares, as a whole sentence."""
    count = len(citations)
    plural = "" if count == 1 else "s"
    return f"This site declares {count} citation{plural} in all."


def _describe_site(citations: Sequence[dict[str, Any]]) -> str:
    """Name a sample of the site's entries and count the rest, for a warning
    that has no better suggestion to make.
    """
    shown = _describe_candidates(citations[:CANDIDATE_LIMIT])
    return f"{_count_citations(citations)[:-1]}, among them {shown}."


def setup(app: Sphinx) -> ExtensionMetadata:
    """Set up the ``citation-card`` directive and the ``doi`` role."""
    # Every non-HTML format gets the pass-through pair, so that the node's
    # literal_block child renders and the builder never meets an unknown node.
    fallback = (
        visit_citation_bibtex_fallback,
        depart_citation_bibtex_fallback,
    )
    app.add_node(
        citation_bibtex,
        html=(visit_citation_bibtex_html, None),
        latex=fallback,
        text=fallback,
        man=fallback,
        texinfo=fallback,
    )
    app.add_directive("citation-card", CitationCard)
    app.add_role("doi", CitationDoiRole())
    # One instance per application, so the footer answer it keeps belongs to
    # this build's configuration and to no other.
    app.connect("html-page-context", CitationCopyScript().add_copy_script)

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
