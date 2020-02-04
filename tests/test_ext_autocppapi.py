"""Tests for documenteer.ext.autocppapi.
"""

import lxml.html
import pytest
from sphinx.util import logging


@pytest.mark.sphinx('html', testroot='autocppapi')
def test_example_page_rendering(app, status, warning):
    """Test against the ``test-autocppapi`` test root.

    These tests ensure that automodapi is generating subsections for
    each API type (Classes, Structs, Variables in this case), and that the
    items have links into the doxygen docs.
    """
    # examples_source_dir = os.path.join(
    #     app.srcdir, app.config.astropy_examples_dir)
    app.verbosity = 2
    logging.setup(app, status, warning)
    app.builder.build_all()

    index_path = app.outdir / 'index.html'
    with open(index_path, 'r') as f:
        html_source = f.read()
    doc = lxml.html.document_fromstring(html_source)

    section = doc.cssselect('#lsst-utils')[0]

    headers = [
        'Classes¶',
        'Structs¶',
        'Variables¶'
    ]

    for div in section.cssselect('div'):
        header = div.cssselect('h3')[0]
        assert header.text_content() in headers

        ul = div.cssselect('ul')[0]

        if header == 'Variables¶':
            li0 = ul.cssselect('a')[0]
            assert li0.attrib['href'] == (
                'cpp-api/classlsst_1_1utils_1_1python_1_1_wrapper_'
                'collection.html#abc61644ff7791a730da4ec8f6057365a'
            )
