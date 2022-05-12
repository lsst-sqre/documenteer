"""Tests for `documenteer.sphinext.lsstdocushare`.
"""


from shutil import rmtree
from tempfile import mkdtemp

import pytest
from sphinx.application import Sphinx

import documenteer.sphinxext.lsstdocushare as lsstdocushare

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock


@pytest.fixture()
def app(request):
    src = mkdtemp()
    doctree = mkdtemp()
    confdir = mkdtemp()
    outdir = mkdtemp()

    Sphinx._log = lambda self, message, wfile, nonl=False: None
    app = Sphinx(
        srcdir=src,
        confdir=None,
        outdir=outdir,
        doctreedir=doctree,
        buildername="html",
    )
    lsstdocushare.setup(app)
    # Stitch together as the sphinx app init() usually does w/ real conf files
    try:
        app.config.init_values()
    except TypeError:
        # Sphinx < 1.6.0
        app.config.init_values(Sphinx._log)

    def fin():
        for dirname in (src, doctree, confdir, outdir):
            rmtree(dirname)

    request.addfinalizer(fin)

    return app


@pytest.fixture()
def inliner(app):
    return Mock(document=Mock(settings=Mock(env=Mock(app=app))))


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (("sqr", "123"), ("SQR-123", "https://sqr-123.lsst.io/")),
        (("dmtn", "123"), ("DMTN-123", "https://dmtn-123.lsst.io/")),
    ],
)
def test_lsstio_link(inliner, test_input, expected):
    """Test link names and URL for technotes on lsst.io."""
    name, content = test_input
    result = lsstdocushare.lsstio_doc_shortlink_role(
        name=name, rawtext=content, text=content, inliner=inliner, lineno=None
    )
    expected_text, expected_uri = expected
    assert result[0][0].astext() == expected_text
    assert result[0][0].attributes["refuri"] == expected_uri


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (("ldm", "151"), ("LDM-151", "https://ls.st/ldm-151")),
        (("lse", "123"), ("LSE-123", "https://ls.st/lse-123")),
        (("lpm", "123"), ("LPM-123", "https://ls.st/lpm-123")),
        (("lts", "123"), ("LTS-123", "https://ls.st/lts-123")),
        (("lep", "123"), ("LEP-123", "https://ls.st/lep-123")),
        (("lsstc", "123"), ("LSSTC-123", "https://ls.st/lsstc-123")),
        (("lcr", "123"), ("LCR-123", "https://ls.st/lcr-123")),
        (("lcn", "123"), ("LCN-123", "https://ls.st/lcn-123")),
        (("dmtr", "123"), ("DMTR-123", "https://ls.st/dmtr-123")),
    ],
)
def test_shortlink(inliner, test_input, expected):
    """Test that the link names and URL are correct."""
    name, content = test_input
    result = lsstdocushare.lsst_doc_shortlink_role(
        name=name, rawtext=content, text=content, inliner=inliner, lineno=None
    )
    expected_text, expected_uri = expected
    assert result[0][0].astext() == expected_text
    assert result[0][0].attributes["refuri"] == expected_uri


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (("document", "123"), ("Document-123", "https://ls.st/document-123")),
        (("minutes", "123"), ("Minutes-123", "https://ls.st/minutes-123")),
        (
            ("collection", "123"),
            ("Collection-123", "https://ls.st/collection-123"),
        ),
    ],
)
def test_titlecase_shortlink(inliner, test_input, expected):
    """Test that the link names and URL are correct for
    roles made with `lsst_doc_shortlink_titlecase_display_role`."""
    name, content = test_input
    result = lsstdocushare.lsst_doc_shortlink_titlecase_display_role(
        name=name, rawtext=content, text=content, inliner=inliner, lineno=None
    )
    expected_text, expected_uri = expected
    assert result[0][0].astext() == expected_text
    assert result[0][0].attributes["refuri"] == expected_uri
