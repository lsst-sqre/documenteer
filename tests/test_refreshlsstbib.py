"""Tests for the refresh-lsst-bib program.
"""

import os

from documenteer.bin.refreshlsstbib import process_bib_files


def test_process_bib_files(tmpdir):
    """Smoke test that downloads and writes bib files into a pytest-fixtured
    temp directory.
    """
    dirname = tmpdir.dirname
    error_count = process_bib_files(dirname)
    assert error_count == 0
    assert os.path.exists(os.path.join(dirname, "books.bib"))
    assert os.path.exists(os.path.join(dirname, "lsst-dm.bib"))
    assert os.path.exists(os.path.join(dirname, "lsst.bib"))
    assert os.path.exists(os.path.join(dirname, "refs.bib"))
    assert os.path.exists(os.path.join(dirname, "refs_ads.bib"))
