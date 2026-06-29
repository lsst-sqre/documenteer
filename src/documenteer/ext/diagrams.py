"""``diagrams`` directive for rendering architectural "diagrams as code".

This extension renders `Diagrams <https://diagrams.mingrammer.com/>`__ source
code (Python scripts that build a ``diagrams.Diagram``) into PNG or SVG images
during the Sphinx build. The output format is chosen project-wide with the
``diagrams_output_format`` config value (``"png"`` by default, or ``"svg"`` for
self-contained vector output in HTML). It provides the ``diagrams`` directive
(both inline and external-file forms) and the `SphinxDiagram` context manager
used by diagram source scripts.
"""

from __future__ import annotations

# This module is vendored from the unmaintained sphinx-diagrams project
# (https://github.com/j-martin/sphinx-diagrams, BSD-2-Clause) so that the
# ``diagrams`` directive keeps working on Sphinx 8-9: the last PyPI release
# (0.4.0) imports ``sha1`` from ``sphinx.util``, which no longer exists in
# Sphinx 9. Besides the Sphinx-compatibility fix, this copy names each rendered
# image after a hash of the diagram source (the approach sphinx.ext.graphviz
# uses), so editing a diagram produces a new filename and re-renders it instead
# of serving a stale cached image.
# See licenses/sphinx-diagrams.txt
import base64
import os
import posixpath
import re
import subprocess
import sys
from hashlib import sha1
from html import escape
from pathlib import Path
from subprocess import CalledProcessError
from typing import TYPE_CHECKING, Any, ClassVar

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.errors import ConfigError, SphinxError
from sphinx.locale import __
from sphinx.util import logging
from sphinx.util.docutils import SphinxDirective, SphinxTranslator

from ..version import __version__

if TYPE_CHECKING:
    from types import TracebackType

    from sphinx.application import Sphinx
    from sphinx.config import Config
    from sphinx.util.typing import ExtensionMetadata

__all__ = ["SphinxDiagram", "setup"]

logger = logging.getLogger(__name__)

#: Output formats supported by the ``diagrams_output_format`` config value.
_VALID_OUTPUT_FORMATS = frozenset({"png", "svg"})

#: Regex matching an ``href``/``xlink:href`` attribute and its value.
_HREF_RE = re.compile(r'((?:xlink:)?href)="([^"]+)"')

#: MIME types for the image suffixes the diagrams library references in SVGs.
_MIME_BY_SUFFIX = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
}


class DiagramsError(SphinxError):
    """Error raised when a diagram fails to render."""

    category = "Diagrams error"


def _validate_config(app: Sphinx, config: Config) -> None:
    """Validate the ``diagrams_output_format`` config value once per build."""
    outformat = config.diagrams_output_format
    if outformat not in _VALID_OUTPUT_FORMATS:
        raise ConfigError(
            __("diagrams_output_format must be one of {}, got {!r}.").format(
                sorted(_VALID_OUTPUT_FORMATS), outformat
            )
        )


def _align_option(argument: str) -> str:
    """Validate the ``align`` option of the ``diagrams`` directive."""
    return directives.choice(argument, ("left", "center", "right"))


class diagrams(nodes.General, nodes.Inline, nodes.Element):  # noqa: N801
    """Docutils node carrying diagram source code and render options."""


class Diagrams(SphinxDirective):
    """Directive that renders a Diagrams (diagrams-as-code) figure.

    The diagram source can be supplied either inline as the directive content
    or as an external Python file referenced by the directive argument.
    """

    has_content = True
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = False
    option_spec: ClassVar = {
        # Accepted for backwards compatibility with sphinx-diagrams. The output
        # filename is now content-hashed and managed by the extension, so this
        # value is ignored.
        "filename": directives.unchanged_required,
        "align": _align_option,
        "class": directives.class_option,
    }

    def run(self) -> list[nodes.Node]:
        """Build a ``diagrams`` node from the directive."""
        document = self.state.document
        if self.arguments:
            if self.content:
                return [
                    document.reporter.warning(
                        __(
                            "The diagrams directive accepts either an "
                            "external file argument or inline content, "
                            "not both."
                        ),
                        line=self.lineno,
                    )
                ]
            rel_filename, filename = self.env.relfn2path(self.arguments[0])
            self.env.note_dependency(rel_filename)
            try:
                with Path(filename).open(encoding="utf-8") as fp:
                    diagram_code = fp.read()
            except OSError:
                return [
                    document.reporter.warning(
                        __(
                            "External diagrams file {!r} not found or "
                            "reading it failed."
                        ).format(filename),
                        line=self.lineno,
                    )
                ]
        else:
            diagram_code = "\n".join(self.content)
            if not diagram_code.strip():
                return [
                    self.state_machine.reporter.warning(
                        __('Ignoring "diagrams" directive without content.'),
                        line=self.lineno,
                    )
                ]

        node = diagrams()
        node["code"] = diagram_code
        node["options"] = {"docname": self.env.docname}
        if "align" in self.options:
            node["align"] = self.options["align"]
        if "class" in self.options:
            node["classes"] = self.options["class"]
        return [node]


def render_diagrams(
    self: SphinxTranslator,
    code: str,
    options: dict[str, Any],
    prefix: str = "diagrams",
    outformat: str = "png",
) -> tuple[str | None, str | None]:
    """Render diagram source code into an image file.

    The output filename embeds a SHA-1 hash of the diagram source, so editing a
    diagram produces a new filename and re-renders the image instead of reusing
    a stale cached file. ``outformat`` selects the image format (``"png"`` or
    ``"svg"``); png and svg renders differ by file extension so they never
    collide on the same hash. Returns a ``(relative_uri, absolute_path)`` tuple
    for the rendered image, or ``(None, None)`` when the diagram could not be
    rendered because Python could not be run.
    """
    hashkey = sha1(code.encode("utf-8"), usedforsecurity=False).hexdigest()
    fname = f"{prefix}-{hashkey}.{outformat}"
    relfn = posixpath.join(self.builder.imgpath, fname)
    image_dir = Path(self.builder.outdir) / self.builder.imagedir
    output_filename = image_dir / fname

    if output_filename.is_file():
        # The same source was already rendered: reuse the cached image.
        return relfn, str(output_filename)

    output_filename.parent.mkdir(parents=True, exist_ok=True)

    # The diagram source is a Python script that builds a ``diagrams.Diagram``
    # through ``SphinxDiagram``. Run it with the image directory as the working
    # directory; the first positional argument tells ``SphinxDiagram`` the
    # filename stem to write, the second disables the diagrams library's "open
    # the rendered image" behavior, and the third selects the output format.
    python_args = [
        sys.executable,
        "-",
        output_filename.stem,
        "false",
        outformat,
    ]

    try:
        completed = subprocess.run(
            python_args,
            input=code.encode(),
            capture_output=True,
            cwd=image_dir,
            env=os.environ.copy(),
            check=True,
        )
    except OSError:
        logger.warning(__("The diagrams Python code could not be run."))
        return None, None
    except CalledProcessError as exc:
        raise DiagramsError(
            __(
                "The diagrams Python code exited with an error.\n"
                "[stderr]\n{}\n[stdout]\n{}"
            ).format(
                exc.stderr.decode("utf-8", "replace"),
                exc.stdout.decode("utf-8", "replace"),
            )
        ) from exc

    if not output_filename.is_file():
        raise DiagramsError(
            __(
                "The diagram in {!r} did not produce the expected output file "
                "{!r}. Ensure the diagram script does not override the output "
                "filename.\n[stderr]\n{}\n[stdout]\n{}"
            ).format(
                options.get("docname"),
                str(output_filename),
                completed.stderr.decode("utf-8", "replace"),
                completed.stdout.decode("utf-8", "replace"),
            )
        )

    if outformat == "svg":
        # graphviz references provider node icons by absolute filesystem path
        # in SVG output, which breaks once the SVG is deployed. Inline the
        # icons so the written file (which is also the on-disk cache) is
        # self-contained.
        _inline_svg_images(output_filename)

    return relfn, str(output_filename)


def _inline_svg_images(svg_path: Path) -> None:
    """Embed externally referenced icon images into an SVG as data URIs.

    The diagrams library references provider node icons by absolute filesystem
    path; graphviz copies those into ``<image xlink:href=...>`` for SVG output,
    so icons break once the SVG is deployed. Rewrite each local file reference
    as a base64 ``data:`` URI so the SVG is self-contained.
    """
    svg_text = svg_path.read_text(encoding="utf-8")

    def _replace(match: re.Match[str]) -> str:
        attr, ref = match.group(1), match.group(2)
        if ref.startswith(("data:", "http:", "https:", "#")):
            return match.group(0)
        ref_path = Path(ref)
        if not ref_path.is_absolute():
            ref_path = svg_path.parent / ref_path
        if not ref_path.is_file():
            return match.group(0)
        mime = _MIME_BY_SUFFIX.get(ref_path.suffix.lower(), "image/png")
        encoded = base64.b64encode(ref_path.read_bytes()).decode("ascii")
        return f'{attr}="data:{mime};base64,{encoded}"'

    new_text = _HREF_RE.sub(_replace, svg_text)
    if new_text != svg_text:
        svg_path.write_text(new_text, encoding="utf-8")


def render_html(
    self: SphinxTranslator,
    node: diagrams,
    code: str,
    options: dict[str, Any],
    prefix: str = "diagrams",
) -> None:
    """Render a ``diagrams`` node into HTML."""
    outformat = self.builder.config.diagrams_output_format
    try:
        fname, _outfn = render_diagrams(self, code, options, prefix, outformat)
    except DiagramsError as exc:
        logger.warning(__("diagrams code %r: %s"), code, exc)
        raise nodes.SkipNode from exc

    # ``body`` is provided by the concrete HTML translator at runtime; the
    # shared SphinxTranslator type used here does not declare it.
    body: list[str] = self.body  # type: ignore[attr-defined]

    if fname is None:
        # The diagram could not be rendered; fall back to showing the source.
        body.append(f"<pre>{escape(code)}</pre>\n")
        raise nodes.SkipNode

    classes = ["diagrams", *node.get("classes", [])]
    align = node.get("align")
    if align:
        body.append(f'<div align="{align}" class="align-{align}">')
    body.append('<div class="diagrams">')
    body.append(
        f'<a href="{fname}">'
        f'<img src="{fname}" class="{" ".join(classes)}" /></a>'
    )
    body.append("</div>\n")
    if align:
        body.append("</div>\n")
    raise nodes.SkipNode


def render_latex(
    self: SphinxTranslator,
    node: diagrams,
    code: str,
    options: dict[str, Any],
    prefix: str = "diagrams",
) -> None:
    """Render a ``diagrams`` node into LaTeX."""
    # pdflatex's \sphinxincludegraphics cannot embed SVG, so always render PNG
    # for LaTeX output regardless of the project's diagrams_output_format.
    try:
        fname, _outfn = render_diagrams(
            self, code, options, prefix, outformat="png"
        )
    except DiagramsError as exc:
        logger.warning(__("diagrams code %r: %s"), code, exc)
        raise nodes.SkipNode from exc

    if fname is None:
        raise nodes.SkipNode

    # ``body`` is provided by the concrete LaTeX translator at runtime; the
    # shared SphinxTranslator type used here does not declare it.
    body: list[str] = self.body  # type: ignore[attr-defined]
    pre = ""
    post = ""
    align = node.get("align")
    if align == "left":
        pre = "{"
        post = r"\hspace*{\fill}}"
    elif align == "right":
        pre = r"{\hspace*{\fill}"
        post = "}"
    elif align == "center":
        pre = r"{\hfill"
        post = r"\hspace*{\fill}}"
    body.append(f"\n{pre}")
    body.append(rf"\sphinxincludegraphics[]{{{fname}}}")
    body.append(f"{post}\n")
    raise nodes.SkipNode


def html_visit_diagrams(self: SphinxTranslator, node: diagrams) -> None:
    """HTML visitor for the ``diagrams`` node."""
    render_html(self, node, node["code"], node["options"])


def latex_visit_diagrams(self: SphinxTranslator, node: diagrams) -> None:
    """LaTeX visitor for the ``diagrams`` node."""
    render_latex(self, node, node["code"], node["options"])


def setup(app: Sphinx) -> ExtensionMetadata:
    """Set up the ``diagrams`` directive."""
    app.add_node(
        diagrams,
        html=(html_visit_diagrams, None),
        latex=(latex_visit_diagrams, None),
    )
    app.add_directive("diagrams", Diagrams)
    # Rebuild trigger "env": switching the format re-processes docs containing
    # diagrams so they pick up the new image extension. Old-format image files
    # are left as harmless orphans (same as the existing source-edit behavior).
    app.add_config_value("diagrams_output_format", "png", "env", str)
    app.connect("config-inited", _validate_config)
    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }


class SphinxDiagram:
    """Context manager wrapping ``diagrams.Diagram`` for diagram scripts.

    Diagram source scripts use this context manager in place of
    ``diagrams.Diagram``. When a script is run by the ``diagrams`` directive,
    the output filename and "show" behavior come from the command-line
    arguments the extension passes; when run standalone, the diagram is named
    after the script and opened for preview.
    """

    def __init__(self, argv: list[str] | None = None, **kwargs: Any) -> None:
        # Import lazily so that importing this extension module does not need
        # the heavy ``diagrams`` package, which is only needed when actually
        # rendering a diagram (e.g. guides don't bundle it).
        from diagrams import Diagram  # noqa: PLC0415

        if argv is None:
            argv = sys.argv
        filename = argv[1] if len(argv) >= 2 else Path(argv[0]).stem
        show = argv[2].lower() == "true" if len(argv) >= 3 else True
        # The 4th argument carries the extension's chosen output format. Guard
        # on its presence so standalone/legacy invocations stay on PNG.
        outformat = argv[3] if len(argv) >= 4 else "png"

        title = kwargs.pop("title", None)
        if title is None:
            title = (
                filename.replace("diagram", "")
                .replace("_", " ")
                .replace("-", " ")
                .replace("  ", " ")
                .title()
            )

        # The extension asserts that an exact ``<stem>.<format>`` file exists
        # afterwards, so the extension-driven format must win over any
        # ``outformat=`` a user diagram script passes.
        kwargs.pop("outformat", None)
        kwargs["outformat"] = outformat

        self.diagram = Diagram(title, show=show, filename=filename, **kwargs)

    def __enter__(self) -> Any:
        return self.diagram.__enter__()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.diagram.__exit__(exc_type, exc_value, traceback)
