"""Guard that every citation copy button's status region stays unseen.

``rubin-citation-copy.js`` reports the outcome of a copy twice: once by
swapping the button's own label, and once into a sibling ``role="status"``
live region, because relabelling a button says nothing to a screen reader
that is not on it. The two are only sensible together if exactly one of them
is visible -- a status region left in the normal flow renders "Copied" a
second time, in plain text, beside the button that already says it.

Nothing in the build enforces that. The span is rendered by a template, the
label is written by a script, and whether the span is seen is decided by a
stylesheet none of them import; a surface added without its visually-hidden
rule compiles, ships, and only shows the duplicate to a reader who presses
the button. That is how the technote sidebar's Cite section shipped visibly
doubled while the guide's two surfaces, styled in a different file, did not.

So this test reads the surfaces from the script itself -- its ``STATUSES``
selector list is the definition of "a region this script writes into" -- and
requires each one to be hidden by some stylesheet Documenteer ships. A fourth
surface is covered the moment the script learns to write to it.

The compiled CSS is a webpack artefact and gitignored, so the SCSS sources
are what a test can hold still.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

COPY_SCRIPT = (
    REPO_ROOT / "src" / "documenteer" / "assets" / "rubin-citation-copy.js"
)

# Both stylesheets Documenteer compiles: the guide's single sheet and the
# technote's entry point with the partials it @uses.
STYLESHEETS = REPO_ROOT / "src" / "assets"

# The standard visually-hidden recipe: a one-pixel box, taken out of the
# flow and clipped away, that assistive technology still reaches. Declaring
# `display: none` or `visibility: hidden` instead would take the live region
# out of the accessibility tree along with the layout, which is the one thing
# the span exists for.
VISUALLY_HIDDEN = {
    "position": "absolute",
    "width": "1px",
    "height": "1px",
    "overflow": "hidden",
    "clip-path": "inset(50%)",
}

_STATUSES = re.compile(r"\bvar\s+STATUSES\s*=(.*?);", re.DOTALL)
_CLASS_SELECTOR = re.compile(r"\.[-\w]+")

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT = re.compile(r"//[^\n]*")
_RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")


def _status_selectors() -> list[str]:
    """Return the class selectors the copy script writes its outcome into."""
    statuses = _STATUSES.search(COPY_SCRIPT.read_text(encoding="utf-8"))
    assert statuses, f"{COPY_SCRIPT.name} declares no STATUSES selector list"
    return _CLASS_SELECTOR.findall(statuses.group(1))


def _declarations(selector: str) -> Iterator[tuple[str, str]]:
    """Yield the ``(property, value)`` pairs every stylesheet declares for
    exactly this selector.

    Only rules whose own subject is the selector count: a rule reaches it
    through a comma-separated list of flat selectors or not at all, which is
    how both stylesheets write these regions.
    """
    for stylesheet in sorted(STYLESHEETS.rglob("*.scss")):
        source = _LINE_COMMENT.sub(
            "", _BLOCK_COMMENT.sub("", stylesheet.read_text(encoding="utf-8"))
        )
        for rule in _RULE.finditer(source):
            subjects = {" ".join(s.split()) for s in rule.group(1).split(",")}
            if selector not in subjects:
                continue
            for declaration in rule.group(2).split(";"):
                if ":" in declaration:
                    prop, _, value = declaration.partition(":")
                    yield prop.strip(), " ".join(value.split())


def test_every_copy_status_region_is_visually_hidden() -> None:
    """Each live region the copy script reports into is styled out of sight,
    so pressing the button shows "Copied" once rather than twice.
    """
    missing = {}
    for selector in _status_selectors():
        declared = dict(_declarations(selector))
        absent = {
            prop: value
            for prop, value in VISUALLY_HIDDEN.items()
            if declared.get(prop) != value
        }
        if absent:
            missing[selector] = absent

    assert missing == {}, (
        "these copy-status live regions are not visually hidden, so the "
        f"outcome label renders beside the button as well: {missing}"
    )
