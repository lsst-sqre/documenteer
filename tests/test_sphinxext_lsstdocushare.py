"""Tests for documenteer.sphinext.lsstdocushare."""


from tempfile import mkdtemp
from shutil import rmtree
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock

import pytest
from sphinx.application import Sphinx

import documenteer.sphinxext.lsstdocushare as lsstdocushare


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
        buildername='html',
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
    [(('ldm', '151'), ('LDM-151', 'http://ls.st/ldm-151')),
     (('lse', '123'), ('LSE-123', 'http://ls.st/lse-123')),
     (('lpm', '123'), ('LPM-123', 'http://ls.st/lpm-123'))])
def test_shortlink(inliner, test_input, expected):

    name, content = test_input
    result = lsstdocushare.lsst_doc_shortlink_role(
        name=name,
        rawtext=content,
        text=content,
        inliner=inliner,
        lineno=None)
    print(expected)
    print(result)
    expected_text, expected_uri = expected
    assert result[0][0].astext() == expected_text
    assert result[0][0].attributes['refuri'] == expected_uri
