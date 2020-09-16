"""Tests for the documenteer.stackdocs.build module (build-stack-docs
executable).
"""

import os
import shutil
import tempfile
from pathlib import Path

import pytest

from documenteer.stackdocs import build
from documenteer.stackdocs.pkgdiscovery import find_package_docs


@pytest.fixture
def temp_dirname():
    temp_dirname = tempfile.mkdtemp()
    yield temp_dirname
    shutil.rmtree(temp_dirname)


def test_link_directories(temp_dirname):
    package_dir = os.path.join(
        os.path.dirname(__file__), "data", "package_alpha"
    )
    package_docs = find_package_docs(package_dir)

    root_packages_path = Path(temp_dirname) / "packages"
    os.makedirs(root_packages_path)

    build.link_directories(root_packages_path, package_docs.package_dirs)
    assert os.path.islink(os.path.join(root_packages_path, "package_alpha"))
    real_path = Path(
        os.path.realpath(os.path.join(root_packages_path, "package_alpha"))
    )
    assert real_path == package_docs.package_dirs["package_alpha"]


def test_link_directories_overwriting(temp_dirname):
    package_dir = os.path.join(
        os.path.dirname(__file__), "data", "package_alpha"
    )
    package_docs = find_package_docs(package_dir)

    root_packages_path = Path(temp_dirname) / "packages"
    os.makedirs(root_packages_path)

    # Make links twice to simulate overwriting existing links
    build.link_directories(root_packages_path, package_docs.package_dirs)
    build.link_directories(root_packages_path, package_docs.package_dirs)

    assert os.path.islink(os.path.join(root_packages_path, "package_alpha"))
    real_path = Path(
        os.path.realpath(os.path.join(root_packages_path, "package_alpha"))
    )
    assert real_path == package_docs.package_dirs["package_alpha"]


def test_remove_existing_links(temp_dirname):
    package_dir = os.path.join(
        os.path.dirname(__file__), "data", "package_alpha"
    )
    package_docs = find_package_docs(package_dir)

    root_packages_path = Path(temp_dirname) / "packages"
    os.makedirs(root_packages_path)

    # Create links
    build.link_directories(root_packages_path, package_docs.package_dirs)
    assert os.path.islink(os.path.join(root_packages_path, "package_alpha"))

    # Remove links
    build.remove_existing_links(root_packages_path)
    assert not os.path.exists(
        os.path.join(root_packages_path, "package_alpha")
    )
