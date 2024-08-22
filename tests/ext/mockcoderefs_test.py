# type: ignore
"""Tests for documenteer.ext.mockcoderefs."""

from __future__ import annotations

from shutil import rmtree
from tempfile import mkdtemp
from typing import Any
from unittest.mock import Mock

import pytest
from sphinx.application import Sphinx

from documenteer.ext import mockcoderefs


@pytest.fixture
def app(request: Any) -> Sphinx:
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
    mockcoderefs.setup(app)
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


@pytest.fixture
def inliner(app: Sphinx) -> Mock:
    return Mock(document=Mock(settings=Mock(env=Mock(app=app))))


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (("lmod", "lsst.afw"), "lsst.afw"),
        (("lmod", "~lsst.afw"), "afw"),
        (("lmod", "~lsst"), "lsst"),
    ],
)
def test_mock_code_ref_role(
    inliner: Mock, test_input: str, expected: str
) -> None:
    role_name, role_content = test_input
    result = mockcoderefs.mock_code_ref_role(
        name=role_name,
        rawtext=role_content,
        text=role_content,
        inliner=inliner,
        lineno=None,
    )
    assert result[0][0].astext() == expected
