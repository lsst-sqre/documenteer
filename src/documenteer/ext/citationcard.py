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

__all__ = ["CitationCard", "setup"]

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
    app.add_directive("citation-card", CitationCard)

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
