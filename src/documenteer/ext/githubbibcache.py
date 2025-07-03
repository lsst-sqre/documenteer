"""A Sphinx extension that caches BibTeX files from GitHub repositories.

These bibfiles can be used with sphinxcontrib-bibtex's ``bibliography``
directive.
"""

from __future__ import annotations

from pathlib import Path
from typing import Self

import requests
from pydantic import BaseModel, Field
from sphinx.application import Sphinx
from sphinx.config import Config
from sphinx.util.typing import ExtensionMetadata

from ..version import __version__

__all__ = ["setup"]


class BibRepo(BaseModel):
    """Model for a configured GitHub repository containing bib files.

    This model corresponds to the ``documenteer_bibfile_github_repos``
    configuration items.
    """

    repo: str = Field(
        ..., description="GitHub repository name", examples=["lsst/texmf"]
    )
    ref: str = Field("main", description="GitHub ref (branch or tag)")
    bibfiles: list[str] = Field(
        description=(
            "List of bibfiles in the repo (POSIX paths relative to the root)"
        ),
        default_factory=list,
    )

    @classmethod
    def parse_config(cls, config: list[dict]) -> list[Self]:
        return [cls.model_validate(item) for item in config]

    def load_bibfiles(self, cache_dir: Path) -> None:
        """Load bibfiles from the GitHub repository into the cache directory.

        Parameters
        ----------
        cache_dir : `pathlib.Path`
            Path to the cache directory.
        """
        for bib_file in self.bibfiles:
            cache_path = self.get_cache_path(bib_file, cache_dir)
            if cache_path.is_file():
                # Already cached
                continue
            self._get_from_github(bib_file, cache_path)

    def get_cached_paths(
        self, cache_dir: Path, *, exist_only: bool = True
    ) -> list[Path]:
        """Return the paths to the locally cached bibfiles from the
        repository.
        """
        paths: list[Path] = []
        for bib_file in self.bibfiles:
            p = self.get_cache_path(bib_file, cache_dir)
            if exist_only and not p.is_file():
                continue
            paths.append(p)
        return paths

    def get_cache_path(self, bib_file: str, cache_dir: Path) -> Path:
        """Get the local cache path for a bib file."""
        return cache_dir / self.repo / self.ref / bib_file

    def _get_from_github(self, bib_file: str, cache_path: Path) -> None:
        url = self._get_raw_url(bib_file)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.unlink(missing_ok=True)
        r = requests.get(url, allow_redirects=True, timeout=10)
        r.raise_for_status()
        content = r.text
        cache_path.write_text(content)

    def _get_raw_url(self, bib_file: str) -> str:
        """Get the raw URL for a bib file on GitHub."""
        return (
            "https://raw.githubusercontent.com"
            f"/{self.repo}/{self.ref}/{bib_file}"
        )


def cache_bibfiles(app: Sphinx, config: Config) -> None:
    """Cache bibfiles from GitHub during config-inited phase."""
    conf_dir = Path(app.confdir)
    # Parse the configuration values
    cache_dir = conf_dir.joinpath(
        Path(config["documenteer_bibfile_cache_dir"])
    )
    repos = BibRepo.parse_config(config["documenteer_bibfile_github_repos"])

    # Load the bibfiles if not in cache
    for repo in repos:
        repo.load_bibfiles(cache_dir)

    # Add the bibfiles to the sphinxcontrib-bibtex configuration
    if "bibtex_bibfiles" not in config:
        config["bibtex_bibfiles"] = []
    for repo in repos:
        for cached_path in repo.get_cached_paths(cache_dir):
            if cached_path not in config["bibtex_bibfiles"]:
                config["bibtex_bibfiles"].append(str(cached_path))


def setup(app: Sphinx) -> ExtensionMetadata:
    """Set up the ``documenteer.ext.autocppapi`` Sphinx extensions."""
    # Configuration values
    app.add_config_value("documenteer_bibfile_github_repos", "", "env", [list])
    app.add_config_value(
        "documenteer_bibfile_cache_dir",
        Path("_build/bibfile-cache"),
        "env",
        [str, Path],
    )
    app.connect("config-inited", cache_bibfiles)

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
