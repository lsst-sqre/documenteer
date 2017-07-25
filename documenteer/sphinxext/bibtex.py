"""Extensions to support LSST bibliographies with
`sphinxcontrib-bibtex <http://sphinxcontrib-bibtex.readthedocs.io>`_.
"""

from pybtex.style.formatting.plain import Style as PlainStyle
from pybtex.style.formatting import toplevel
from pybtex.plugin import register_plugin
from pybtex.style.template import (
    join, field, sentence, tag, optional_field, href, first_of, optional
)


class LsstBibtexStyle(PlainStyle):
    """Bibtex style that understands ``docushare`` fields in LSST
    bibliographies.
    """

    def format_docushare(self, e):
        default_url = join['https://ls.st/', field('handle', raw=True)]

        template = toplevel[
            sentence[tag('b')['[', href[default_url, field('handle')], ']']],
            self.format_names('author'),
            self.format_title(e, 'title'),
            sentence[field('year')],
            sentence[optional_field('note')],
            # Use URL if we have it, else provide own
            first_of[
                optional[
                    self.format_url(e)
                ],
                # define our own URL
                sentence['URL', href[default_url, default_url]]
            ]
        ]
        return template.format_data(e)


def setup(app):
    """Add this plugin to the Sphinx application."""
    register_plugin('pybtex.style.formatting', 'lsst_aa', LsstBibtexStyle)
