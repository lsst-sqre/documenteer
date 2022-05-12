"""Tests for the documenteer.stackdocs.doxygentag module.
"""

import importlib.util
from pathlib import Path
from zipfile import ZipFile

import pytest

from documenteer.stackdocs.doxygentag import get_tag_entity_names

if importlib.util.find_spec("sphinxcontrib.doxylink"):
    doxylink_installed = True
else:
    doxylink_installed = False


@pytest.fixture(scope="session")
def tag_path(tmp_path_factory):
    zipped_path = Path(__file__).parent / "data" / "doxygen.tag.zip"
    base_dir = tmp_path_factory.mktemp("doxygentag")

    with ZipFile(zipped_path) as tagzip:
        tagzip.extract("doxygen.tag", path=base_dir)

    return base_dir / "doxygen.tag"


@pytest.mark.skipif(
    doxylink_installed is False,
    reason="sphinxcontrib.doxylink must be installed",
)
@pytest.mark.skip(reason="Not currently working")
def test_get_tag_entity_names_all(tag_path):
    names = get_tag_entity_names(tag_path)
    assert "lsst::afw::table::Schema" in names


@pytest.mark.skipif(
    doxylink_installed is False,
    reason="sphinxcontrib.doxylink must be installed",
)
@pytest.mark.skip(reason="Not currently working")
def test_get_tag_entity_names_files(tag_path):
    names = get_tag_entity_names(tag_path, kinds=["file"])
    assert "lsst::afw::table::Schema" not in names
    for name in names:
        assert name.endswith(".h")
