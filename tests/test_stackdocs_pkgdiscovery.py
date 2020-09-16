"""Tests for the documenteer.stackdocs.pkgdiscovery module.
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from documenteer.stackdocs.pkgdiscovery import (
    NoPackageDocs,
    find_package_docs,
    list_packages_in_eups_table,
)


@pytest.fixture
def temp_dirname():
    temp_dirname = tempfile.mkdtemp()
    yield temp_dirname
    shutil.rmtree(temp_dirname)


def test_find_package_docs():
    package_dir = Path(__file__).parent / "data" / "package_alpha"
    package_docs = find_package_docs(package_dir)

    assert "package_alpha" in package_docs.package_dirs
    expected_package_dir = package_dir / "doc" / "package_alpha"
    assert package_docs.package_dirs["package_alpha"] == expected_package_dir

    assert "package.alpha" in package_docs.module_dirs
    expected_module_dir = package_dir / "doc" / "package.alpha"
    assert package_docs.module_dirs["package.alpha"] == expected_module_dir

    assert "package_alpha" in package_docs.static_doc_dirs
    expected_static_dir = package_dir / "doc" / "_static/" / "package_alpha"
    assert package_docs.static_doc_dirs["package_alpha"] == expected_static_dir

    expected_doxygen_conf_in = package_dir / "doc" / "doxygen.conf.in"
    assert package_docs.doxygen_conf_in_path == expected_doxygen_conf_in

    assert package_docs.doxygen_conf_path is None


def test_find_package_docs_nonexistent():
    """Test when an EUPS package does not have a doc/manifest.yaml file."""
    package_dir = Path(__file__).parent / "data" / "package_beta"
    with pytest.raises(NoPackageDocs):
        find_package_docs(package_dir)


def test_list_packages_in_eups_table():
    table_text = (
        "# commented line"
        "setupRequired(afw)"
        "setupRequired(display_ds9)"
        "setupRequired(meas_extensions_photometryKron)"
    )

    listed_packages = list_packages_in_eups_table(table_text)
    assert "afw" in listed_packages
    assert "display_ds9" in listed_packages
    assert "meas_extensions_photometryKron" in listed_packages
    assert len(listed_packages) == 3
