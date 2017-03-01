"""Utilities for sphinx configuration."""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import re

import os
import git


TICKET_BRANCH_PATTERN = re.compile('^tickets/([A-Z]+-[0-9]+)$')

# does it start with vN and look like a version tag?
TAG_PATTERN = re.compile('^v\d')


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


def form_ltd_edition_name(git_ref_name=None):
    """Form the LSST the Docs edition name for this branch, using the same
    logic as LTD Keeper does for transforming branch names into edition names.

    Parameters
    ----------
    git_ref_name : `str`
       Name of the git branch (or git ref, in general, like a tag) that.

    Notes
    -----
    The LTD Keeper (github.com/lsst-sqre/ltd-keeper) logic is being replicated
    here because Keeper is server side code and this is client-side and it's
    not yet clear this warrants being refactored into a common dependency.

    See ``keeper.utils.auto_slugify_edition``.
    """
    if git_ref_name is None:
        name = read_git_branch()
    else:
        name = git_ref_name

    # First, try to use the JIRA ticket number
    m = TICKET_BRANCH_PATTERN.match(name)
    if m is not None:
        return m.group(1)

    # Or use a tagged version
    m = TAG_PATTERN.match(name)
    if m is not None:
        return name

    if name == 'master':
        # using this terminology for LTD Dasher
        name = 'Current'

    # Otherwise, reproduce the LTD slug
    name = name.replace('/', '-')
    name = name.replace('_', '-')
    name = name.replace('.', '-')
    return name
