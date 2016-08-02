"""Utilities for sphinx configuration."""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
import git


def read_git_branch():
    """Obtain the current branch name from the Git repository. If on Travis CI,
    use the ``TRAVIS_BRANCH`` environment variable.
    """
    if os.getenv('TRAVIS'):
        return os.getenv('TRAVIS_BRANCH')
    else:
        try:
            repo = git.repo.base.Repo(search_parent_directories=True)
            return repo.active_branch.name
        except:
            return ''


def read_git_commit_timestamp():
    """Obtain the timestamp from the current git commit."""
    repo = git.repo.base.Repo(search_parent_directories=True)
    return repo.head.commit.committed_datetime
