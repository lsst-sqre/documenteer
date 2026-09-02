"""``citation-card`` directive for displaying a user guide's citation.

A site published with a DOI is that DOI's landing page, and DataCite asks a
landing page to show a full bibliographic citation with the DOI written as a
resolvable ``https://doi.org/`` link. This directive is the page-level surface
that does it: it renders one of the site's ``[[project.citations]]`` entries as
a card carrying the citation, the entry's label, and its note.

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
from sphinx.util.docutils import SphinxDirective

from ..version import __version__

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sphinx.application import Sphinx
    from sphinx.util.typing import ExtensionMetadata
    from sphinx.writers.html5 import HTML5Translator

__all__ = ["CitationCard", "citation_bibtex", "setup"]

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
            self._warn(
                "this site declares no citations, so there is nothing to "
                "render. Describe the work this site is the landing page "
                "for in a [[project.citations]] entry in documenteer.toml."
            )
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

        for citation in citations:
            if citation.get("label") == label:
                return citation
        self._warn(
            f'no citation is labelled "{label}". This site\'s citations are '
            f"labelled {_describe_labels(citations)}."
        )
        return None

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
            paragraph += nodes.reference("", url, refuri=url, internal=False)
        return paragraph

    def _warn(self, message: str) -> None:
        """Log a warning about this directive, located at its own source."""
        logger.warning(
            "citation-card: %s",
            message,
            location=self.get_location(),
            type=WARNING_TYPE,
            subtype=WARNING_SUBTYPE,
        )


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


def _describe_labels(citations: Sequence[dict[str, Any]]) -> str:
    """Name the labels a directive argument can select, for a warning."""
    labels = [
        citation["label"] for citation in citations if citation.get("label")
    ]
    if not labels:
        return "no citation declares a label"
    return ", ".join(f'"{label}"' for label in labels)


def setup(app: Sphinx) -> ExtensionMetadata:
    """Set up the ``citation-card`` directive."""
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

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
