"""Tests for documenteer.sphinext.jira

Based on sphinx-issue (Steven Loria). See :file:`/licenses/sphinx-issue.txt`
for licensing information.
"""


from shutil import rmtree
from tempfile import mkdtemp

import pytest
from sphinx.application import Sphinx

import documenteer.sphinxext.jira as jira

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock


URI = "https://jira.lsstcorp.org/browse/{ticket}"


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
    jira.setup(app)
    # Stitch together as the sphinx app init() usually does w/ real conf files
    app.config._raw_config = {"jira_uri_template": URI}
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


def test_jira_single(inliner):
    result = jira.jira_role(
        name=None, rawtext="", text="DM-1234", lineno=None, inliner=inliner
    )
    link = result[0][0]
    assert link.astext() == "DM-1234"
    assert link.attributes["refuri"] == URI.format(ticket="DM-1234")


def test_jira_two(inliner):
    result = jira.jira_role(
        name=None,
        rawtext="",
        text="DM-1234,DM-5678",
        inliner=inliner,
        lineno=None,
    )
    link1 = result[0][0]
    assert link1.astext() == "DM-1234"
    assert link1.attributes["refuri"] == URI.format(ticket="DM-1234")

    sep = result[0][1]
    assert sep.astext() == " and "

    link2 = result[0][2]
    assert link2.astext() == "DM-5678"
    assert link2.attributes["refuri"] == URI.format(ticket="DM-5678")


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("DM-ABCD,DM-EFGH,DM-IJKL", "DM-ABCD, DM-EFGH, and DM-IJKL"),
        (
            "DM-ABCD,DM-EFGH,DM-IJKL,DM-MNOP",
            "DM-ABCD, DM-EFGH, DM-IJKL, and DM-MNOP",
        ),
    ],
)
def test_jira_text(inliner, test_input, expected):
    result = jira.jira_role(
        name=None,
        rawtext="",
        text=test_input,
        inliner=inliner,
        lineno=None,
    )
    text = "".join([r.astext() for r in result[0]])
    assert expected == text


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("DM-ABCD", "[DM-ABCD]"),
        ("DM-ABCD,DM-EFGH", "[DM-ABCD, DM-EFGH]"),
        ("DM-ABCD,DM-EFGH,DM-IJKL", "[DM-ABCD, DM-EFGH, DM-IJKL]"),
        (
            "DM-ABCD,DM-EFGH,DM-IJKL,DM-MNOP",
            "[DM-ABCD, DM-EFGH, DM-IJKL, DM-MNOP]",
        ),
    ],
)
def test_jira_bracket_text(inliner, test_input, expected):
    result = jira.jira_bracket_role(
        name=None,
        rawtext="",
        text=test_input,
        inliner=inliner,
        lineno=None,
    )
    text = "".join([r.astext() for r in result[0]])
    assert expected == text


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("DM-ABCD", "(DM-ABCD)"),
        ("DM-ABCD,DM-EFGH", "(DM-ABCD, DM-EFGH)"),
        ("DM-ABCD,DM-EFGH,DM-IJKL", "(DM-ABCD, DM-EFGH, DM-IJKL)"),
        (
            "DM-ABCD,DM-EFGH,DM-IJKL,DM-MNOP",
            "(DM-ABCD, DM-EFGH, DM-IJKL, DM-MNOP)",
        ),
    ],
)
def test_jira_parens_text(inliner, test_input, expected):
    result = jira.jira_parens_role(
        name=None,
        rawtext="",
        text=test_input,
        inliner=inliner,
        lineno=None,
    )
    text = "".join([r.astext() for r in result[0]])
    assert expected == text
