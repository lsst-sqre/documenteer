"""Tests for documenteer.stackdocs.rootdiscovery.
"""

import os
import pathlib
import tempfile

import pytest

from documenteer.stackdocs.rootdiscovery import (
    _has_conf_py,
    _search_parents,
    discover_conf_py_directory,
    discover_package_doc_dir,
)


def test_has_conf_py():
    """Test conf.py detection in _has_conf.py."""
    with tempfile.TemporaryDirectory() as tempdir:
        initial_dir = pathlib.Path(tempdir)
        assert _has_conf_py(initial_dir) is False
        _install_conf_py(initial_dir)
        assert _has_conf_py(initial_dir) is True


def test_search_parents_found():
    """Test _search_parents where a conf.py can be found."""
    with tempfile.TemporaryDirectory() as tempdir:
        root_dir = pathlib.Path(tempdir)
        os.makedirs(str(root_dir / "a" / "b"))
        _install_conf_py(root_dir)
        assert _search_parents(root_dir / "a" / "b") == root_dir


def test_search_parents_not_found():
    """Test _search_parents where a conf.py **cannot** be found."""
    with tempfile.TemporaryDirectory() as tempdir:
        root_dir = pathlib.Path(tempdir)
        os.makedirs(str(root_dir / "a" / "b"))
        with pytest.raises(FileNotFoundError):
            _search_parents(root_dir / "a" / "b")


def test_discover_package_doc_dir():
    """Test discover_package_doc_dir when a conf.py exists in the initial
    directory.
    """
    with tempfile.TemporaryDirectory() as tempdir:
        root_dir = pathlib.Path(tempdir)
        _install_conf_py(root_dir)
        expected = pathlib.Path(tempdir).resolve()
        assert discover_package_doc_dir(tempdir) == str(expected)


def test_discover_package_doc_dir_not_found():
    """Test discover_package_doc_dir when a conf.py does not exist."""
    with tempfile.TemporaryDirectory() as tempdir:
        with pytest.raises(FileNotFoundError):
            discover_package_doc_dir(tempdir)


def test_discover_package_doc_dir_search_parents():
    """Test discover_package_doc_dir when conf.py is in a parent directory."""
    with tempfile.TemporaryDirectory() as tempdir:
        root_dir = pathlib.Path(tempdir)
        _install_conf_py(root_dir)
        os.makedirs(str(root_dir / "a" / "b"))
        expected = pathlib.Path(tempdir).resolve()
        assert discover_package_doc_dir(root_dir / "a" / "b") == str(expected)


def test_discover_package_doc_dir_toplevel_doc():
    """Test discover_package_doc_dir when a doc/ dir exists in the current
    working directory.
    """
    with tempfile.TemporaryDirectory() as tempdir:
        root_dir = pathlib.Path(tempdir)
        os.makedirs(str(root_dir / "doc"))
        _install_conf_py(root_dir / "doc")
        expected = pathlib.Path(tempdir).resolve() / "doc"
        assert discover_package_doc_dir(tempdir) == str(expected)


def test_discover_conf_py_directory():
    """Test discover_conf_py_directory when a conf.py exists in the initial
    directory.
    """
    with tempfile.TemporaryDirectory() as tempdir:
        root_dir = pathlib.Path(tempdir)
        _install_conf_py(root_dir)
        expected = pathlib.Path(tempdir).resolve()
        assert discover_conf_py_directory(tempdir) == str(expected)


def test_discover_conf_py_directory_not_found():
    """Test discover_conf_py_directory when a conf.py does not exist."""
    with tempfile.TemporaryDirectory() as tempdir:
        with pytest.raises(FileNotFoundError):
            discover_conf_py_directory(tempdir)


def test_discover_conf_py_directory_search_parents():
    """Test discover_conf_py_directory if conf.py is in a parent directory."""
    with tempfile.TemporaryDirectory() as tempdir:
        root_dir = pathlib.Path(tempdir)
        _install_conf_py(root_dir)
        os.makedirs(str(root_dir / "a" / "b"))
        expected = pathlib.Path(tempdir).resolve()
        assert discover_conf_py_directory(root_dir / "a" / "b") == str(
            expected
        )


def _install_conf_py(directory):
    with open(str(directory / "conf.py"), "w") as f:
        f.write("# test conf.py")
