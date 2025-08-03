"""Support for Rubin BibTeX files for pybtex/sphinxcontrib.bibtex."""

__all__ = ["setup"]

import typing

import pybtex.style.formatting.plain
from pybtex.database import Entry, Person
from pybtex.plugin import register_plugin
from pybtex.style.formatting import toplevel
from pybtex.style.template import (
    FieldIsMissing,
    Node,
    field,
    first_of,
    href,
    join,
    node,
    optional,
    optional_field,
    sentence,
    tag,
)
from sphinx.application import Sphinx
from sphinx.util.typing import ExtensionMetadata

from ..version import __version__


@node
def truncated_names(
    children: list[Node], context: typing.Any, role: str, **kwargs: typing.Any
) -> Node:
    """Return formatted names, truncating long author lists."""
    assert not children  # noqa: S101 (matches pybtex original)

    try:
        persons = context["entry"].persons[role]
    except KeyError:
        raise FieldIsMissing(role, context["entry"]) from None

    # If there are more than 7 authors we return the first 3.
    if len(persons) > 7:
        persons = persons[:3] + [Person("others")]
    style = context["style"]
    formatted_names = [
        style.format_name(person, style.abbreviate_names) for person in persons
    ]
    return join(**kwargs)[formatted_names].format_data(context)


class LsstBibtexStyle(pybtex.style.formatting.plain.Style):
    """Bibtex style that understands ``docushare`` fields in LSST
    bibliographies.
    """

    # Allows a mapping of journal or series name found in the bibtex file
    # to a more usable name for the Sphinx output. In particular ADS returns
    # bib entries that assume latex commands exist to convert from \apj
    # to ApJ or Astrophys. J as needed (allowing each style to decide how
    # to report journal names).
    bib_name_to_usable_name: typing.ClassVar = {
        r"\actaa": "Acta Astron.",
        r"\aap": "A&A",
        r"\aaps": "A&AS",
        r"\aj": "AJ",
        r"\ao": "Appl. Opt.",
        r"\apj": "ApJ",
        r"\apjl": "ApJL",
        r"\apjs": "ApJS",
        r"\apss": "Ap&SS",
        r"\araa": "ARA&A",
        r"\icarus": "Icarus",
        r"\memsai": "Mem. Soc. Ast. Italiana",
        r"\mnras": "MNRAS",
        r"\nat": "Nature",
        r"\pasa": "PASA",
        r"\pasj": "PASJ",
        r"\pasp": "PASP",
        r"\physrep": "Phys. Rep.",
        r"\prd": "Phys. Rev. D.",
        r"\procspie": "Proc. SPIE",
        "Society of Photo-Optical Instrumentation Engineers (SPIE) Conference"
        " Series": "Proc. SPIE",
    }

    def _rewrite_field(self, e: Entry, field: str) -> None:
        """Rewrite the field contents based on the bib name map."""
        if field in e.fields:
            bib_name = e.fields[field]
            if modified_name := self.bib_name_to_usable_name.get(bib_name):
                e.fields[field] = modified_name

    def get_article_template(self, e: Entry) -> Node:
        # Fix up the journal name before rendering.
        # In particular journal entries from ADS tend to use \apj style
        # latex commands which need expanding.
        self._rewrite_field(e, "journal")
        return super().get_article_template(e)

    def get_inproceedings_template(self, e: Entry) -> Node:
        # Potentially modify the series string before formatting it.
        self._rewrite_field(e, "series")
        self._rewrite_field(e, "booktitle")
        return super().get_inproceedings_template(e)

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

    def format_names(self, role: str, as_sentence: bool = True) -> Node:  # noqa: FBT001, FBT002
        # Copied from pybtex but using a different names function that
        # caps the number of authors.
        formatted_names = truncated_names(
            role, sep=", ", sep2=" and ", last_sep=", and "
        )
        if as_sentence:
            return sentence[formatted_names]
        else:
            return formatted_names


def setup(app: Sphinx) -> ExtensionMetadata:
    """Add this plugin to the Sphinx application."""
    register_plugin("pybtex.style.formatting", "lsst_aa", LsstBibtexStyle)

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
