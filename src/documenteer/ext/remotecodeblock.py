"""``remote-code-block`` directive that works like ``literalinclude``, but
supports getting content over https.
"""

__all__ = ["setup"]

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from sphinx.directives.code import LiteralIncludeReader, container_wrapper
from sphinx.util import logging, parselinenos
from sphinx.util.nodes import set_source_info

from ..requestsutils import requests_retry_session
from ..version import __version__

logger = logging.getLogger(__name__)


class RemoteCodeBlock(Directive):
    """Directive that works like ``literalinclude`` to show a code block, but
    supports getting content over https.

    Notes
    -----
    This code is based on Sphinx's LiteralInclude. Copyright 2007-2018 by the
    Sphinx team.
    """

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {
        "dedent": int,
        "linenos": directives.flag,
        "lineno-start": int,
        "lineno-match": directives.flag,
        "tab-width": int,
        "language": directives.unchanged_required,
        "encoding": directives.encoding,
        "pyobject": directives.unchanged_required,
        "lines": directives.unchanged_required,
        "start-after": directives.unchanged_required,
        "end-before": directives.unchanged_required,
        "start-at": directives.unchanged_required,
        "end-at": directives.unchanged_required,
        "prepend": directives.unchanged_required,
        "append": directives.unchanged_required,
        "emphasize-lines": directives.unchanged_required,
        "caption": directives.unchanged,
        "class": directives.class_option,
        "name": directives.unchanged,
        "diff": directives.unchanged_required,
    }

    @property
    def env(self):
        """Reference to the ``.BuildEnvironment`` object.

        FIXME: this can be removed with Sphinx 1.8.0.
        """
        return self.state.document.settings.env

    @property
    def config(self):
        """Reference to the `Config`` object.

        FIXME: this can be removed with Sphinx 1.8.0.
        """
        return self.env.config

    def run(self):
        """Run the ``remote-code-block`` directive."""
        document = self.state.document
        if not document.settings.file_insertion_enabled:
            return [
                document.reporter.warning(
                    "File insertion disabled", line=self.lineno
                )
            ]

        try:
            location = self.state_machine.get_source_and_line(self.lineno)

            # Customized for RemoteCodeBlock
            url = self.arguments[0]
            reader = RemoteCodeBlockReader(url, self.options, self.config)
            text, lines = reader.read(location=location)

            retnode = nodes.literal_block(text, text)
            set_source_info(self, retnode)
            if self.options.get("diff"):  # if diff is set, set udiff
                retnode["language"] = "udiff"
            elif "language" in self.options:
                retnode["language"] = self.options["language"]
            retnode["linenos"] = (
                "linenos" in self.options
                or "lineno-start" in self.options
                or "lineno-match" in self.options
            )
            retnode["classes"] += self.options.get("class", [])
            extra_args = retnode["highlight_args"] = {}
            if "emphasize-lines" in self.options:
                hl_lines = parselinenos(self.options["emphasize-lines"], lines)
                if any(i >= lines for i in hl_lines):
                    logger.warning(
                        "line number spec is out of range(1-%d): %r"
                        % (lines, self.options["emphasize-lines"]),
                        location=location,
                    )
                extra_args["hl_lines"] = [x + 1 for x in hl_lines if x < lines]
            extra_args["linenostart"] = reader.lineno_start

            if "caption" in self.options:
                caption = self.options["caption"] or self.arguments[0]
                retnode = container_wrapper(self, retnode, caption)

            # retnode will be note_implicit_target that is linked from caption
            # and numref.  when options['name'] is provided, it should be
            # primary ID.
            self.add_name(retnode)

            return [retnode]

        except Exception as exc:
            return [document.reporter.warning(str(exc), line=self.lineno)]


class RemoteCodeBlockReader(LiteralIncludeReader):
    """Reader for content used by `RemoteCodeBlock`."""

    def read_file(self, url, location=None):
        """Read content from the web by overriding
        `LiteralIncludeReader.read_file`.
        """
        response = requests_retry_session().get(url, timeout=10.0)
        response.raise_for_status()
        text = response.text
        if "tab-width" in self.options:
            text = text.expandtabs(self.options["tab-width"])

        return text.splitlines(True)


def setup(app):
    app.add_directive("remote-code-block", RemoteCodeBlock)

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
