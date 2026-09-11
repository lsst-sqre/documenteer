"""Tests for the guide stylesheet's source,
:file:`src/assets/rubin-guide/styles/rubin-pydata-theme.scss`.

The compiled CSS is a webpack artefact and is gitignored, so the SCSS is what
a test can hold still. These tests cover the rules that have to outweigh
pydata-sphinx-theme's own stylesheet, where losing is silent: the browser
simply drops the declaration, and only a built site shows it.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

STYLESHEET = (
    Path(__file__).parent.parent
    / "src"
    / "assets"
    / "rubin-guide"
    / "styles"
    / "rubin-pydata-theme.scss"
)

CARD_CLASS = "documenteer-citation-card"

# pydata-sphinx-theme resets the horizontal padding of every docutils
# container: `.docutils.container{...padding-left:unset;padding-right:unset}`.
# The citation card is built as a docutils container, so this is the
# specificity a rule must reach before the card's own padding survives.
THEME_CONTAINER_RESET_SPECIFICITY = (0, 2, 0)

_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}")
_COMBINATOR_RE = re.compile(r"[\s>+~]+")
_CARD_SUBJECT_RE = re.compile(rf"\.{CARD_CLASS}(?![-\w])")
_HORIZONTAL_PADDING_RE = re.compile(
    r"(?:^|;)\s*padding(?:-left|-right|-inline(?:-start|-end)?)?\s*:",
    re.MULTILINE,
)


def _rules(source: str) -> Iterator[tuple[str, str]]:
    """Yield a ``(selector, declarations)`` pair for every selector in the
    stylesheet, one per comma-separated selector in each rule.

    Rules nested in an at-rule (``@media``) are yielded on their own, since
    the at-rule's braces keep its prelude from reading as a selector.
    """
    for rule in _RULE_RE.finditer(_COMMENT_RE.sub("", source)):
        for selector in rule.group(1).split(","):
            yield " ".join(selector.split()), rule.group(2)


def _specificity(selector: str) -> tuple[int, int, int]:
    """Return a selector's CSS specificity as ``(ids, classes, elements)``.

    Counts ids, then classes, attribute selectors and pseudo-classes, then
    element names and pseudo-elements -- enough for the flat selectors this
    stylesheet writes, which use no ``:is()``, ``:not()`` or ``:where()``.
    """
    ids = re.findall(r"#[-\w]+", selector)
    classes = re.findall(r"\.[-\w]+|\[[^\]]*\]|(?<!:):[-\w]+", selector)
    elements = re.findall(r"(?:^|[\s>+~])[a-zA-Z][-\w]*|::[-\w]+", selector)
    return len(ids), len(classes), len(elements)


def _targets_card(selector: str) -> bool:
    """Whether the selector's subject is the citation card element itself,
    rather than something inside it or one of its ``__``-suffixed parts.
    """
    subject = _COMBINATOR_RE.split(selector)[-1]
    return bool(_CARD_SUBJECT_RE.search(subject))


def test_card_padding_outweighs_the_theme_container_reset() -> None:
    """Some rule gives the citation card horizontal padding at a specificity
    the theme's ``.docutils.container`` reset cannot beat.
    """
    rules = [
        (selector, declarations)
        for selector, declarations in _rules(
            STYLESHEET.read_text(encoding="utf-8")
        )
        if _targets_card(selector)
        and _HORIZONTAL_PADDING_RE.search(declarations)
    ]
    assert rules, f"no rule sets horizontal padding on .{CARD_CLASS}"

    winner = max(rules, key=lambda rule: _specificity(rule[0]))
    assert _specificity(winner[0]) >= THEME_CONTAINER_RESET_SPECIFICITY, (
        f"the card's padding is written as `{winner[0]}`, which "
        "pydata-sphinx-theme's `.docutils.container` reset outweighs "
        "whatever the stylesheet order; chain the classes the HTML writer "
        "stamps on the card instead"
    )


def test_card_padding_needs_no_important() -> None:
    """The card wins on specificity, not by shouting over the theme."""
    for selector, declarations in _rules(
        STYLESHEET.read_text(encoding="utf-8")
    ):
        if _targets_card(selector):
            assert "!important" not in declarations, (
                f"`{selector}` forces its declarations with !important"
            )
