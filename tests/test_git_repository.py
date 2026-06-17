"""Tests for documenteer.conf._utils.GitRepository.compute_last_modified."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from git import Actor, Repo

from documenteer.conf._utils import GitRepository

ACTOR = Actor("Test Author", "test@example.com")


def _commit(repo: Repo, paths: list[Path], message: str, date: str) -> None:
    """Stage ``paths`` and commit them at a fixed author/committer date.

    ``date`` is an ISO 8601 string understood by Git, e.g.
    ``"2024-06-01T00:00:00+0000"``.
    """
    repo.index.add([str(p) for p in paths])
    repo.index.commit(
        message,
        author=ACTOR,
        committer=ACTOR,
        author_date=date,
        commit_date=date,
    )


def test_source_only(tmp_path: Path) -> None:
    """The last-modified date for a single tracked file is its commit date."""
    repo = Repo.init(tmp_path)
    page = tmp_path / "index.rst"
    page.write_text("Page\n")
    _commit(repo, [page], "Add page", "2024-06-01T00:00:00+0000")

    git_repo = GitRepository(tmp_path)
    result = git_repo.compute_last_modified([page])
    assert result == datetime(2024, 6, 1, tzinfo=UTC)


def test_max_of_source_and_include(tmp_path: Path) -> None:
    """The date is the most-recent commit across the source and its
    dependencies (the includes behavior).
    """
    repo = Repo.init(tmp_path)
    page = tmp_path / "index.rst"
    page.write_text("Page\n")
    _commit(repo, [page], "Add page", "2024-06-01T00:00:00+0000")

    snippet = tmp_path / "snippet.txt"
    snippet.write_text("snippet\n")
    _commit(repo, [snippet], "Add snippet", "2024-07-15T00:00:00+0000")

    git_repo = GitRepository(tmp_path)

    # Source alone reflects only its own commit.
    assert git_repo.compute_last_modified([page]) == datetime(
        2024, 6, 1, tzinfo=UTC
    )

    # Source + later-modified include reflects the include's newer commit.
    assert git_repo.compute_last_modified([page, snippet]) == datetime(
        2024, 7, 15, tzinfo=UTC
    )


def test_uncommitted_file_skipped(tmp_path: Path) -> None:
    """Untracked/uncommitted files are skipped; with no tracked paths the
    result is None.
    """
    repo = Repo.init(tmp_path)
    page = tmp_path / "index.rst"
    page.write_text("Page\n")
    _commit(repo, [page], "Add page", "2024-06-01T00:00:00+0000")

    new_file = tmp_path / "draft.rst"
    new_file.write_text("Draft\n")  # written but never committed

    git_repo = GitRepository(tmp_path)

    # The uncommitted file alone yields None.
    assert git_repo.compute_last_modified([new_file]) is None

    # The uncommitted file is ignored when mixed with a tracked file.
    assert git_repo.compute_last_modified([page, new_file]) == datetime(
        2024, 6, 1, tzinfo=UTC
    )


def test_path_outside_working_tree_skipped(tmp_path: Path) -> None:
    """Paths outside the Git working tree are ignored defensively."""
    repo = Repo.init(tmp_path)
    page = tmp_path / "index.rst"
    page.write_text("Page\n")
    _commit(repo, [page], "Add page", "2024-06-01T00:00:00+0000")

    outside = tmp_path.parent / "outside.txt"

    git_repo = GitRepository(tmp_path)
    assert git_repo.compute_last_modified([outside]) is None
    assert git_repo.compute_last_modified([page, outside]) == datetime(
        2024, 6, 1, tzinfo=UTC
    )


def test_cache_reuse(tmp_path: Path) -> None:
    """Per-path results are cached so shared dependencies resolve once."""
    repo = Repo.init(tmp_path)
    page = tmp_path / "index.rst"
    page.write_text("Page\n")
    _commit(repo, [page], "Add page", "2024-06-01T00:00:00+0000")

    git_repo = GitRepository(tmp_path)
    assert not git_repo._last_modified_cache

    first = git_repo.compute_last_modified([page])
    key = str(page.resolve())
    assert key in git_repo._last_modified_cache
    assert git_repo._last_modified_cache[key] == first

    # A second call returns the same cached value.
    second = git_repo.compute_last_modified([page])
    assert second == first
