"""Tests for the documenteer.stackdocs.pkgdiscovery module.
"""

from pathlib import Path
import tempfile
import shutil

import pytest

from documenteer.stackdocs.pkgdiscovery import (
    find_package_docs, NoPackageDocs)


@pytest.fixture
def temp_dirname():
    temp_dirname = tempfile.mkdtemp()
    yield temp_dirname
    shutil.rmtree(temp_dirname)


def test_find_package_docs():
    package_dir = Path(__file__).parent / 'data' / 'package_alpha'
    package_docs = find_package_docs(package_dir)

    assert 'package_alpha' in package_docs.package_dirs
    expected_package_dir = package_dir / 'doc' / 'package_alpha'
    assert package_docs.package_dirs['package_alpha'] == expected_package_dir

    assert 'package.alpha' in package_docs.module_dirs
    expected_module_dir = package_dir / 'doc' / 'package.alpha'
    assert package_docs.module_dirs['package.alpha'] == expected_module_dir

    assert 'package_alpha' in package_docs.static_doc_dirs
    expected_static_dir = package_dir / 'doc' / '_static/' / 'package_alpha'
    assert package_docs.static_doc_dirs['package_alpha'] == expected_static_dir


def test_find_package_docs_nonexistent():
    """Test when an EUPS package does not have a doc/manifest.yaml file.
    """
    package_dir = Path(__file__).parent / 'data' / 'package_beta'
    with pytest.raises(NoPackageDocs):
        find_package_docs(package_dir)
