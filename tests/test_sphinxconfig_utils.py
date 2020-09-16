from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import os
from datetime import datetime

import pytest

from documenteer.sphinxconfig.utils import (
    form_ltd_edition_name,
    get_filepaths_with_extension,
    get_project_content_commit_date,
    read_git_commit_timestamp,
    read_git_commit_timestamp_for_file,
)


@pytest.mark.parametrize(
    "git_ref,name",
    [
        ("master", "Current"),
        ("tickets/DM-6120", "DM-6120"),
        ("v1.2.3", "v1.2.3"),
        ("draft/v1.2.3", "draft-v1-2-3"),
    ],
)
def test_form_ltd_edition_name(git_ref, name):
    assert name == form_ltd_edition_name(git_ref_name=git_ref)


def test_git_commit_timestamp():
    """Smoke-test read_git_commit_timestamp using Documenteer's own Git
    repository.
    """
    timestamp = read_git_commit_timestamp()
    assert isinstance(timestamp, datetime)


def test_git_commit_timestamp_for_file():
    """Smoke-test read_git_commit_timestamp_for_file with README.rst in
    Documenteer's own Git repo.
    """
    test_dir = os.path.dirname(__file__)
    readme_path = os.path.abspath(os.path.join(test_dir, "..", "README.rst"))
    timestamp = read_git_commit_timestamp_for_file(readme_path)
    assert isinstance(timestamp, datetime)


def test_git_commit_timestamp_for_file_nonexistent():
    """Smoke-test read_git_commit_timestamp_for_file with README.rst in
    Documenteer's own Git repo.
    """
    path = "doesnt_exist.txt"
    with pytest.raises(IOError):
        read_git_commit_timestamp_for_file(path)


def test_get_filepaths_with_extension():
    repo_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    filepaths = get_filepaths_with_extension("py", root_dir=repo_dir)
    assert os.path.join("tests", "test_sphinxconfig_utils.py") in filepaths
    assert "README.rst" not in filepaths


def test_get_project_content_commit_date():
    """Smoke test using the documenteer repo."""
    repo_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    print("repo_dir", repo_dir)
    commit_date = get_project_content_commit_date(root_dir=repo_dir)
    assert isinstance(commit_date, datetime)
