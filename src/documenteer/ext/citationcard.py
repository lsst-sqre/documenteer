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
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util import logging
from sphinx.util.docutils import SphinxDirective, SphinxRole
from sphinx.util.nodes import split_explicit_title

from ..version import __version__

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sphinx.application import Sphinx
    from sphinx.util.typing import ExtensionMetadata
    from sphinx.writers.html5 import HTML5Translator

__all__ = ["CitationCard", "CitationDoiRole", "citation_bibtex", "setup"]

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

    The optional argument is the ``label`` of the ``[[project.citations]]``
    entry to render. With no argument the directive renders the site's
    preferred citation — the work the site asks readers to cite — which is
    what a "Citing this site" page wants.

    An argument that matches no entry, and a site with no preferred entry, are
    warnings rather than errors: the citation metadata a site displays should
    never be the reason a page fails to build, and the warning carries a
    subtype so a site can suppress it deliberately.
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
        label = self.arguments[0].strip() if self.arguments else None
        citation = self._select(label)
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

    def _select(self, label: str | None) -> dict[str, Any] | None:
        """Choose the citation to render, warning and returning `None` when
        no entry answers.
        """
        citations = self._citations()
        if not citations:
            self._warn(NO_CITATIONS_MESSAGE)
            return None

        if label is None:
            preferred = self.config.html_context.get(
                "documenteer_preferred_citation"
            )
            if preferred is None:
                self._warn(
                    "no citation is marked `preferred = true`, so there is "
                    "no default entry to render. Mark the citation this site "
                    "asks readers to use with `preferred = true` in "
                    "documenteer.toml -- or with `self = true` when the site "
                    "really is that DOI's registered landing page -- or give "
                    "the directive a label to render: "
                    f"{_describe_labels(citations)}."
                )
            return preferred

        citation = _find_citation(citations, label)
        if citation is None:
            self._warn(_unknown_label_message(label, citations))
        return citation

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
    prose rather than as an identifier.

    The role always names a label -- there is no default entry -- because a
    role appears mid-sentence, where an implicit subject would be a guess at
    which of the site's works the sentence is about. Labels are matched
    exactly and case-sensitively against ``documenteer_citations``, the same
    lookup `CitationCard` does.

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
        has_title, title, label = split_explicit_title(self.text)
        label = label.strip()
        citation = self._select(label)
        doi_url = citation.get("doi_url") if citation else None
        if doi_url is None:
            # The warning has already been logged; leaving the text in place
            # keeps the sentence that holds the role readable, which a
            # missing or half-built link would not.
            return [nodes.Text(title if has_title else label)], []
        text = title if has_title else doi_url
        return [_location_reference(doi_url, text)], []

    def _select(self, label: str) -> dict[str, Any] | None:
        """Choose the citation to link, warning and returning `None` when no
        entry answers with a DOI.
        """
        citations = self.config.html_context.get("documenteer_citations") or []
        if not citations:
            self._warn(NO_CITATIONS_MESSAGE)
            return None

        citation = _find_citation(citations, label)
        if citation is None:
            self._warn(_unknown_label_message(label, citations))
            return None

        if not citation.get("doi_url"):
            self._warn(_no_doi_message(label, citation))
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


def _find_citation(
    citations: Sequence[dict[str, Any]], label: str
) -> dict[str, Any] | None:
    """Return the declared citation carrying this label, or `None`.

    Matching is exact and case-sensitive. A label is a short display string an
    author writes in :file:`documenteer.toml` and copies into a page, so a
    near-miss is a typo in one of the two places, and matching it loosely
    would render a citation the page did not ask for.

    Both surfaces resolve a label through here, so a label that selects a card
    always selects the same entry for a role.
    """
    for citation in citations:
        if citation.get("label") == label:
            return citation
    return None


def _unknown_label_message(
    label: str, citations: Sequence[dict[str, Any]]
) -> str:
    """Compose the warning for a label no declared citation carries."""
    return (
        f'no citation is labelled "{label}". This site\'s citations are '
        f"labelled {_describe_labels(citations)}."
    )


def _no_doi_message(label: str, citation: dict[str, Any]) -> str:
    """Compose the warning for an entry the ``doi`` role cannot link because
    the entry declares no DOI.

    The message names the entry's ``url`` when it has one, because that is the
    link the author expected and the one they can write by hand instead.
    """
    url = citation.get("url")
    located = (
        f" It is located by url ({url}) rather than by a DOI." if url else ""
    )
    return (
        f'the citation labelled "{label}" declares no DOI, so there is no '
        f"DOI to link.{located} Give the entry a `doi`, or write the link "
        "with ordinary hyperlink syntax, or render the whole entry with a "
        "citation-card, which displays whichever location the entry has."
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


def _describe_labels(citations: Sequence[dict[str, Any]]) -> str:
    """Name the labels a directive argument can select, for a warning."""
    labels = [
        citation["label"] for citation in citations if citation.get("label")
    ]
    if not labels:
        return "no citation declares a label"
    return ", ".join(f'"{label}"' for label in labels)


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

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
