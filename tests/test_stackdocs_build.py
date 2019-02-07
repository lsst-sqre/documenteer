"""Tests for the documenteer.stackdocs.build module (build-stack-docs
executable).
"""

import os
import shutil
import tempfile

import pytest

from documenteer.stackdocs import build


@pytest.fixture
def temp_dirname():
    temp_dirname = tempfile.mkdtemp()
    yield temp_dirname
    shutil.rmtree(temp_dirname)


def test_find_package_docs():
    package_dir = os.path.join(
        os.path.dirname(__file__),
        'data',
        'package_alpha')
    package_docs = build.find_package_docs(package_dir)

    assert 'package_alpha' in package_docs.package_dirs
    expected_package_dir = os.path.join(package_dir, 'doc', 'package_alpha')
    assert package_docs.package_dirs['package_alpha'] == expected_package_dir

    assert 'package.alpha' in package_docs.module_dirs
    expected_module_dir = os.path.join(package_dir, 'doc', 'package.alpha')
    assert package_docs.module_dirs['package.alpha'] == expected_module_dir

    assert 'package_alpha' in package_docs.static_dirs
    expected_static_dir = os.path.join(package_dir,
                                       'doc',
                                       '_static/package_alpha')
    assert package_docs.static_dirs['package_alpha'] == expected_static_dir


def test_find_package_docs_nonexistent():
    """Test when an EUPS package does not have a doc/manifest.yaml file.
    """
    package_dir = os.path.join(
        os.path.dirname(__file__),
        'data',
        'package_beta')
    with pytest.raises(build.NoPackageDocs):
        build.find_package_docs(package_dir)


def test_link_directories(temp_dirname):
    package_dir = os.path.join(
        os.path.dirname(__file__),
        'data',
        'package_alpha')
    package_docs = build.find_package_docs(package_dir)

    root_packages_path = os.path.join(temp_dirname, 'packages')

    os.makedirs(root_packages_path)
    build.link_directories(root_packages_path, package_docs.package_dirs)
    assert os.path.islink(os.path.join(root_packages_path, 'package_alpha'))
    real_path = os.path.realpath(
        os.path.join(root_packages_path, 'package_alpha'))
    assert real_path == package_docs.package_dirs['package_alpha']


def test_link_directories_overwriting(temp_dirname):
    package_dir = os.path.join(
        os.path.dirname(__file__),
        'data',
        'package_alpha')
    package_docs = build.find_package_docs(package_dir)

    root_packages_path = os.path.join(temp_dirname, 'packages')

    os.makedirs(root_packages_path)

    # Make links twice to simulate overwriting existing links
    build.link_directories(root_packages_path, package_docs.package_dirs)
    build.link_directories(root_packages_path, package_docs.package_dirs)

    assert os.path.islink(os.path.join(root_packages_path, 'package_alpha'))
    real_path = os.path.realpath(
        os.path.join(root_packages_path, 'package_alpha'))
    assert real_path == package_docs.package_dirs['package_alpha']


def test_remove_existing_links(temp_dirname):
    package_dir = os.path.join(
        os.path.dirname(__file__),
        'data',
        'package_alpha')
    package_docs = build.find_package_docs(package_dir)

    root_packages_path = os.path.join(temp_dirname, 'packages')

    os.makedirs(root_packages_path)

    # Create links
    build.link_directories(root_packages_path, package_docs.package_dirs)
    assert os.path.islink(os.path.join(root_packages_path, 'package_alpha'))

    # Remove links
    build.remove_existing_links(root_packages_path)
    assert not os.path.exists(os.path.join(root_packages_path,
                                           'package_alpha'))


def test_list_packages_in_eups_table():
    table_text = (
        "# commented line"
        "setupRequired(afw)"
        "setupRequired(display_ds9)"
        "setupRequired(meas_extensions_photometryKron)"
    )

    listed_packages = build.list_packages_in_eups_table(table_text)
    assert 'afw' in listed_packages
    assert 'display_ds9' in listed_packages
    assert 'meas_extensions_photometryKron' in listed_packages
    assert len(listed_packages) == 3
