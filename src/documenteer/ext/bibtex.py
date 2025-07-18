"""Support for Rubin BibTeX files for pybtex/sphinxcontrib.bibtex."""

import pybtex.style.formatting.plain
from pybtex.database import Entry
from pybtex.plugin import register_plugin
from pybtex.style.formatting import toplevel
from pybtex.style.template import (
    field,
    first_of,
    href,
    join,
    optional,
    optional_field,
    sentence,
    tag,
)
from sphinx.application import Sphinx
from sphinx.util.typing import ExtensionMetadata

from ..version import __version__

__all__ = ["setup"]


class LsstBibtexStyle(pybtex.style.formatting.plain.Style):
    """Bibtex style that understands ``docushare`` fields in LSST
    bibliographies.
    """

    def format_docushare(self, e: Entry) -> str:
        default_url = join["https://ls.st/", field("handle", raw=True)]

        template = toplevel[
            sentence[tag("b")["[", href[default_url, field("handle")], "]"]],
            self.format_names("author"),
            self.format_title(e, "title"),
            sentence[field("year")],
            sentence[optional_field("note")],
            # Use URL if we have it, else provide own
            first_of[
                optional[self.format_url(e)],
                # define our own URL
                sentence["URL", href[default_url, default_url]],
            ],
        ]
        return template.format_data(e)


def setup(app: Sphinx) -> ExtensionMetadata:
    """Add this plugin to the Sphinx application."""
    register_plugin("pybtex.style.formatting", "lsst_aa", LsstBibtexStyle)

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
