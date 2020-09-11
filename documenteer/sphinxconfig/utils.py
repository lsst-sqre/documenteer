"""Utilities for sphinx configuration."""

import logging
import os
import re

import git
from sphinx.util.matching import Matcher

TICKET_BRANCH_PATTERN = re.compile(r"^tickets/([A-Z]+-[0-9]+)$")

# does it start with vN and look like a version tag?
TAG_PATTERN = re.compile(r"^v\d")


def read_git_branch():
    """Obtain the current branch name from the Git repository. If on Travis CI,
    use the ``TRAVIS_BRANCH`` environment variable.
    """
    if os.getenv("TRAVIS"):
        return os.getenv("TRAVIS_BRANCH")
    else:
        try:
            repo = git.repo.base.Repo(search_parent_directories=True)
            return repo.active_branch.name
        except Exception:
            return ""


def read_git_commit_timestamp(repo_path=None):
    """Obtain the timestamp from the current head commit of a Git repository.

    Parameters
    ----------
    repo_path : `str`, optional
        Path to the Git repository. Leave as `None` to use the current working
        directory.

    Returns
    -------
    commit_timestamp : `datetime.datetime`
        The datetime of the head commit.
    """
    repo = git.repo.base.Repo(path=repo_path, search_parent_directories=True)
    head_commit = repo.head.commit
    return head_commit.committed_datetime


def read_git_commit_timestamp_for_file(filepath, repo_path=None):
    """Obtain the timestamp for the most recent commit to a given file in a
    Git repository.

    Parameters
    ----------
    filepath : `str`
        Repository-relative path for a file.
    repo_path : `str`, optional
        Path to the Git repository. Leave as `None` to use the current working
        directory.

    Returns
    -------
    commit_timestamp : `datetime.datetime`
        The datetime of a the most recent commit to the given file.

    Raises
    ------
    IOError
        Raised if the ``filepath`` does not exist in the Git repository.
    """
    repo = git.repo.base.Repo(path=repo_path, search_parent_directories=True)
    head_commit = repo.head.commit

    # most recent commit datetime of the given file
    for commit in head_commit.iter_parents(filepath):
        return commit.committed_datetime

    # Only get here if git could not find the file path in the history
    raise IOError("File {} not found".format(filepath))


def get_filepaths_with_extension(extname, root_dir="."):
    """Get relative filepaths of files in a directory, and sub-directories,
    with the given extension.

    Parameters
    ----------
    extname : `str`
        Extension name (e.g. 'txt', 'rst'). Extension comparison is
        case-insensitive.
    root_dir : `str`, optional
        Root directory. Current working directory by default.

    Returns
    -------
    filepaths : `list` of `str`
        File paths, relative to ``root_dir``, with the given extension.
    """
    # needed for comparison with os.path.splitext
    if not extname.startswith("."):
        extname = "." + extname

    # for case-insensitivity
    extname = extname.lower()

    root_dir = os.path.abspath(root_dir)

    selected_filenames = []
    for dirname, sub_dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if os.path.splitext(filename)[-1].lower() == extname:
                full_filename = os.path.join(dirname, filename)
                selected_filenames.append(
                    os.path.relpath(full_filename, start=root_dir)
                )
    return selected_filenames


def get_project_content_commit_date(root_dir=".", exclusions=None):
    """Get the datetime for the most recent commit to a project that
    affected Sphinx content.

    *Content* is considered any file with one of these extensions:

    - ``rst`` (README.rst and LICENSE.rst are excluded)
    - ``ipynb``
    - ``png``
    - ``jpeg``
    - ``jpg``
    - ``svg``
    - ``gif``

    This function allows project infrastructure and configuration files to be
    updated without changing the timestamp.

    Parameters
    ----------
    root_dir : `str`, optional
        Root directory. This is the current working directory by default.
    exclusions : `list` of `str`, optional
        List of file paths or directory paths to ignore.

    Returns
    -------
    commit_date : `datetime.datetime`
        Datetime of the most recent content commit.

    Raises
    ------
    RuntimeError
        Raised if no content files are found.
    """
    logger = logging.getLogger(__name__)

    # Supported 'content' extensions
    extensions = ("rst", "ipynb", "png", "jpeg", "jpg", "svg", "gif")

    content_paths = []
    for extname in extensions:
        content_paths += get_filepaths_with_extension(
            extname, root_dir=root_dir
        )

    # Known files that should be excluded; lower case for comparison
    exclude = Matcher(
        exclusions if exclusions else ["readme.rst", "license.rst"]
    )

    # filter out excluded files
    content_paths = [
        p
        for p in content_paths
        if not (exclude(p) or exclude(p.split(os.path.sep)[0]))
    ]
    logger.debug("Found content paths: {}".format(", ".join(content_paths)))

    if not content_paths:
        raise RuntimeError("No content files found in {}".format(root_dir))

    commit_datetimes = []
    for filepath in content_paths:
        try:
            datetime = read_git_commit_timestamp_for_file(
                filepath, repo_path=root_dir
            )
            commit_datetimes.append(datetime)
        except IOError:
            logger.warning(
                "Could not get commit for {}, skipping".format(filepath)
            )

    if not commit_datetimes:
        raise RuntimeError("No content commits could be found")

    latest_datetime = max(commit_datetimes)

    return latest_datetime


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

    if name == "master":
        # using this terminology for LTD Dasher
        name = "Current"

    # Otherwise, reproduce the LTD slug
    name = name.replace("/", "-")
    name = name.replace("_", "-")
    name = name.replace(".", "-")
    return name
