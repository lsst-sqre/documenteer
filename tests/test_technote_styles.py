"""Guard Rubin's technote stylesheet against rules nothing renders.

Documenteer styles Rubin technotes on top of the ``technote`` package's
theme, so most of what it styles is markup that package renders and only a
little is markup Documenteer's own template overrides add. When either side
reorganizes its templates, a rule for the element that went away keeps
compiling and keeps shipping in every technote's stylesheet, and no build
ever says so -- which is how ``.rubin-technote-global-breadcrumbs``,
``.rubin-technote-version-info``, and ``.mobile-rubin-technote-logo``
outlived the template that was their only source of markup.

This test is the build failure that was missing: every class the technote
SCSS styles has to be written by something that can put it on a page.
"""

from __future__ import annotations

import re
from pathlib import Path

import technote

REPO_ROOT = Path(__file__).parent.parent

SCSS_COMPONENTS = (
    REPO_ROOT / "src" / "assets" / "rubin-technote" / "styles" / "components"
)

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT = re.compile(r"//[^\n]*")
_AT_RULE = re.compile(r"\s*@")
_CLASS = re.compile(r"\.(-?[A-Za-z_][A-Za-z0-9_-]*)")


def _styled_classes(scss: Path) -> set[str]:
    """Return the classes a SCSS partial writes rules for.

    Only the selector ahead of a ``{`` is read, so a file name mentioned in a
    comment or an ``@use`` is never mistaken for a class, and an at-rule that
    opens a block (``@media``, ``@supports``) contributes nothing of its own
    -- the selectors nested inside it are ordinary selector lines.
    """
    source = _LINE_COMMENT.sub("", _BLOCK_COMMENT.sub("", scss.read_text()))
    return {
        name
        for line in source.splitlines()
        if "{" in line and not _AT_RULE.match(line)
        for name in _CLASS.findall(line.split("{", 1)[0])
    }


def _rendered_markup() -> str:
    """Return the text of everything that can put a class on a technote page.

    That is Documenteer's technote template overrides and the browser scripts
    it ships, plus the whole installed ``technote`` package -- its theme
    templates, the templates its Sphinx extensions render, and the Python and
    JavaScript that build nodes. Stylesheets are deliberately excluded: a
    class that only a stylesheet names is exactly the dead rule being hunted.
    """
    documenteer = REPO_ROOT / "src" / "documenteer"
    technote_package = Path(technote.__file__).parent
    paths = [
        *(documenteer / "templates" / "technote").rglob("*.html"),
        *(documenteer / "assets").glob("*.js"),
        *documenteer.rglob("*.py"),
        *technote_package.rglob("*.html"),
        *technote_package.rglob("*.jinja"),
        *technote_package.rglob("*.js"),
        *technote_package.rglob("*.py"),
    ]
    return "\n".join(path.read_text(encoding="utf-8") for path in paths)


def test_every_styled_class_is_rendered_somewhere() -> None:
    """Every class the technote SCSS styles is written by a template or a
    script, so the compiled stylesheet ships no rule for markup that no
    longer exists.
    """
    markup = _rendered_markup()

    unrendered = {
        scss.name: sorted(
            name
            for name in _styled_classes(scss)
            if not re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", markup)
        )
        for scss in sorted(SCSS_COMPONENTS.glob("*.scss"))
    }

    assert {file: names for file, names in unrendered.items() if names} == {}
