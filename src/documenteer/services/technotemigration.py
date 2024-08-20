"""Technote migration service."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from documenteer.storage.authordb import AuthorDb
from documenteer.storage.localtemplates import LocalProjectTemplates
from documenteer.storage.technotetoml import TechnoteTomlFile

from .technoteauthor import TechnoteAuthorService


class TechnoteMigrationService:
    """A service for migrating technotes to the new Technote-based format."""

    def __init__(self, technote_dir: Path, author_db: AuthorDb) -> None:
        self.root_dir = technote_dir
        self.author_db = author_db

    def migrate(self, *, author_ids: list[str]) -> None:
        """Migrate a technote.yaml to technote.toml."""
        yaml_path = self.root_dir / "metadata.yaml"
        toml_path = self.root_dir / "technote.toml"
        original_metadata = yaml.safe_load(yaml_path.read_text())

        self._migrate_toml(original_metadata, toml_path, author_ids)
        self._overwrite_template_files(original_metadata)

    def _migrate_toml(
        self,
        original_metadata: dict[str, Any],
        toml_path: Path,
        author_ids: list[str],
    ) -> None:
        toml_file = self._create_toml_file(original_metadata)
        toml_file.save(toml_path)

        # Add authors
        author_service = TechnoteAuthorService(toml_file, self.author_db)
        for author_id in author_ids:
            try:
                author_service.add_author_by_id(author_id)
            except ValueError:
                print(
                    f"Warning: Author {author_id} not found in authordb.yaml"
                )
        toml_file.save(self.root_dir / "technote.toml")

        print("✅ technote.toml")

        content = self._upgrade_content(original_metadata)
        self.root_dir.joinpath("index.rst").write_text(content)
        print("✅ index.rst")

    def _create_toml_file(
        self, original_metadata: dict[str, Any]
    ) -> TechnoteTomlFile:
        """Create a technote.toml file."""
        try:
            github_url = original_metadata["github_url"]
        except KeyError as e:
            raise ValueError(
                "metadata.yaml does not contain github_url"
            ) from e

        try:
            number = original_metadata["serial_number"]
        except KeyError as e:
            raise ValueError(
                "metadata.yaml does not contain serial_number"
            ) from e

        try:
            series = original_metadata["series"]
        except KeyError as e:
            raise ValueError("metadata.yaml does not contain series") from e

        toml_content = (
            "[technote]\n"
            f'id = "{series}-{number}"\n'
            f'series_id = "{series}"\n'
            f'canonical_url = "https://{series.lower()}-{number}.lsst.io/"\n'
            f'github_url = "{github_url}"\n'
            f'github_default_branch = "main"\n'
            f'organization.name = "Vera C. Rubin Observatory"\n'
            f'organization.ror = "https://ror.org/048g3cy84"\n'
            f'license.id = "CC-BY-4.0"\n'
        )

        return TechnoteTomlFile(toml_content)

    def _upgrade_content(self, original_metadata: dict[str, Any]) -> str:
        """Upgrade index.rst."""
        index_rst_path = self.root_dir / "index.rst"
        if not index_rst_path.exists():
            raise RuntimeError("index.rst does not exist")
        rst_content = index_rst_path.read_text()

        # Add title
        try:
            title = original_metadata["doc_title"]
        except KeyError as e:
            raise ValueError("metadata.yaml does not contain doc_title") from e
        underlines = "#" * len(title)
        rst_title = f"{underlines}\n{title}\n{underlines}\n\n"

        # Add abstract
        try:
            abstract = original_metadata["description"]
        except KeyError as e:
            raise ValueError(
                "metadata.yaml does not contain a description"
            ) from e
        rst_abstract = f".. abstract::\n\n   {abstract}\n\n"

        # Filter out lines of content with old formatting concerns
        lines = rst_content.splitlines()
        # Patterns for lines that should be dropped
        drop_lines = [
            r"^:tocdepth:",
            r"^\.\. Please do not modify tocdepth",
            r"\.\. sectnum::",
            r"^   :style: lsst_aa",
        ]
        new_lines: list[str] = [
            line
            for line in lines
            if not any(re.match(p, line) for p in drop_lines)
        ]

        # Replace lines related to the bibliography
        replacements = [
            (
                r"^\.\. rubric:: References",
                "References\n==========\n",
            ),
            (r"^\.\. bibliography::", ".. bibliography::\n"),
        ]
        for pattern, replacement in replacements:
            new_lines = [
                replacement if re.match(pattern, line) else line
                for line in new_lines
            ]

        # Prepend title and abstract
        return rst_title + rst_abstract + "\n".join(new_lines)

    def _overwrite_template_files(
        self, original_metadata: dict[str, Any]
    ) -> None:
        """Write/overwrite files with template content."""
        templates = LocalProjectTemplates()

        url_path = urlparse(original_metadata["github_url"]).path
        parts = url_path.split("/")
        github_namespace = "/".join(parts[1:3])
        github_namespace = github_namespace.removesuffix(".git")

        series = original_metadata["series"]
        serial_number = original_metadata["serial_number"]

        cookiecutter_context = {
            "title": original_metadata["doc_title"],
            "series": original_metadata["series"],
            "serial_number": original_metadata["serial_number"],
            "description": original_metadata["description"],
            "url": f"https://{series.lower()}-{serial_number}.lsst.io/",
            "github_namespace": github_namespace,
        }
        context = {"cookiecutter": cookiecutter_context}

        # Write/overwrite files
        templates.write(
            name="technote/dependabot.yml",
            path=self.root_dir / ".github" / "dependabot.yml",
            context=context,
        )
        print("✅ .github/dependabot.yml")

        templates.write(
            name="technote/ci.yaml",
            path=self.root_dir / ".github" / "workflows" / "ci.yaml",
            context=context,
        )
        print("✅ .github/workflows/ci.yaml")

        templates.write(
            name="technote/pre-commit-config.yaml",
            path=self.root_dir / ".pre-commit-config.yaml",
            context=context,
        )
        print("✅ .pre-commit-config.yaml")

        templates.write(
            name="technote/gitignore",
            path=self.root_dir / ".gitignore",
            context=context,
        )
        print("✅ .gitignore")

        templates.write(
            name="technote/conf.py",
            path=self.root_dir / "conf.py",
            context=context,
        )
        print("✅ conf.py")

        templates.write(
            name="technote/Makefile",
            path=self.root_dir / "Makefile",
            context=context,
        )
        print("✅ Makefile")

        templates.write(
            name="technote/README.rst",
            path=self.root_dir / "README.rst",
            context=context,
        )
        print("✅ README.rst")

        templates.write(
            name="technote/requirements.txt",
            path=self.root_dir / "requirements.txt",
            context=context,
        )
        print("✅ requirements.txt")

        templates.write(
            name="technote/tox.ini",
            path=self.root_dir / "tox.ini",
            context=context,
        )
        print("✅ tox.ini")

    def delete_deprecated_files(self) -> None:
        """Delete deprecated files."""
        deprecated_files = [
            "metadata.yaml",
            ".travis.yml",
        ]
        for file in deprecated_files:
            path = self.root_dir / file
            self._delete_file(path)

        deprecated_dirs = [
            "lsstbib",
        ]
        for dirname in deprecated_dirs:
            path = self.root_dir / dirname
            self._delete_directory(path)

    def _delete_file(self, path: Path) -> None:
        """Delete a file."""
        if path.exists():
            path.unlink()
            print(f"🗑️ {path}")

    def _delete_directory(self, path: Path) -> None:
        """Delete a directory."""
        if path.exists():
            shutil.rmtree(path)
            print(f"🗑️ {path}")
