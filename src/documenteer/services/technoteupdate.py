"""Service for bringing a technote repository up to the current standard."""

from __future__ import annotations

import re
import shutil
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

import yaml

from documenteer.storage.authordb import AuthorDb
from documenteer.storage.localtemplates import LocalProjectTemplates
from documenteer.storage.technotetoml import TechnoteTomlFile

from .technoteauthor import TechnoteAuthorService

__all__ = [
    "CONF_PY_PATH",
    "TEMPLATE_CONF_PY_CONTENTS",
    "TOOLING_TEMPLATES",
    "FileOutcome",
    "TechnoteUpdateService",
    "UpdateStatus",
]

TOOLING_TEMPLATES: dict[str, str] = {
    ".github/dependabot.yml": "technote/dependabot.yml",
    ".github/workflows/ci.yaml": "technote/ci.yaml",
    ".pre-commit-config.yaml": "technote/pre-commit-config.yaml",
    ".gitignore": "technote/gitignore",
    "Makefile": "technote/Makefile",
    "requirements.txt": "technote/requirements.txt",
    "tox.ini": "technote/tox.ini",
}
"""The standard tooling files, keyed by their path from the technote root.

These are the files a technote does not write: they configure the build, the
linters, and continuous integration, and every technote is meant to carry the
same ones. :file:`README.rst` and the content file are absent because they are
the technote's own writing, and :file:`conf.py` because it is the one tooling
file a technote is expected to extend.
"""

CONF_PY_PATH = "conf.py"
"""The path, from the technote root, of the file `CONF_PY_TEMPLATE` writes."""

CONF_PY_TEMPLATE = "technote/conf.py"
"""The template for a technote's conf.py."""

_CONF_PY_HEADER = (
    "# See the Documenteer docs for how to customize conf.py:\n"
    "# https://documenteer.lsst.io/technotes/\n"
    "\n"
)

_CONF_PY_IMPORTS = (
    "from documenteer.conf.technote import *  # noqa: F403",
    "from documenteer.conf.technote import *  # noqa F401 F403",
    "from documenteer.conf.technote import *  # noqa: F401, F403",
    "from documenteer.conf.technote import *  # noqa: F401,F403",
)

TEMPLATE_CONF_PY_CONTENTS: frozenset[str] = frozenset(
    f"{header}{import_line}\n"
    for header in ("", _CONF_PY_HEADER)
    for import_line in _CONF_PY_IMPORTS
)
"""Every conf.py Documenteer and its cookiecutters have generated.

A :file:`conf.py` matching one of these byte for byte says nothing the current
template does not, so rewriting it loses nothing. Anything else is a
technote's own Sphinx configuration, and is left alone. The set is the product
of the header comment (present or absent) with each spelling of the ``noqa``
comment that has shipped, because the two varied independently across
Documenteer releases and the ``lsst/templates`` cookiecutters.
"""


class UpdateStatus(Enum):
    """What an update did to one file."""

    updated = "updated"
    """The file was written, because it was absent or out of date."""

    unchanged = "unchanged"
    """The file already held what the update would have written."""

    skipped = "skipped"
    """The file was named by ``--ignore-file``, and was not examined."""

    differs = "differs"
    """The file is the technote's own, and was left rather than overwritten.

    Only :file:`conf.py` reaches this status: it is the one standard file a
    technote is expected to extend.
    """


@dataclass(frozen=True)
class FileOutcome:
    """What an update did to one file, and which file it was."""

    path: str
    """The file's path from the technote root, in POSIX form.

    This is the spelling the command reports and the spelling
    ``--ignore-file`` matches, so that what a reader sees is what they can
    type back.
    """

    status: UpdateStatus
    """What the update did to the file."""

    @property
    def changed(self) -> bool:
        """Whether the file was written — or would be, on a real run."""
        return self.status is UpdateStatus.updated


def _normalize_path(name: str) -> str:
    """Spell a user-supplied path the way an outcome reports it."""
    return PurePosixPath(name.replace("\\", "/")).as_posix().removeprefix("./")


def _github_namespace(github_url: str) -> str:
    """Reduce a GitHub repository URL to its ``owner/repo`` namespace."""
    parts = urlparse(github_url).path.split("/")
    return "/".join(parts[1:3]).removesuffix(".git")


class TechnoteUpdateService:
    """A service for bringing a technote up to the current standard.

    A technote repository falls behind in two different ways, and this
    service covers both. One is age: a technote written before December 2023
    still carries a :file:`metadata.yaml`, and has to be converted. The other
    is drift: a modern technote's tooling files were written by whichever
    Documenteer generated them, and the standard has moved since. Either way
    the destination is the same, and reaching it a second time changes
    nothing.

    Parameters
    ----------
    technote_dir
        The root of the technote repository.
    author_db
        The Rubin author database, used by the legacy conversion to fill in
        the authors it is given.
    """

    def __init__(self, technote_dir: Path, author_db: AuthorDb) -> None:
        self.root_dir = technote_dir
        self.author_db = author_db
        self._templates = LocalProjectTemplates()

    @property
    def is_legacy(self) -> bool:
        """Whether this technote is still in the metadata.yaml format.

        A directory holding both files has already been converted, and its
        leftover :file:`metadata.yaml` is only a file the conversion was
        never asked to delete; it is not converted a second time.
        """
        return (
            not (self.root_dir / "technote.toml").is_file()
            and (self.root_dir / "metadata.yaml").is_file()
        )

    def refresh_tooling(
        self,
        *,
        ignore_files: Iterable[str] = (),
        dry_run: bool = False,
    ) -> list[FileOutcome]:
        """Rewrite a modern technote's tooling files from the templates.

        The technote's own writing — :file:`README.rst` and the content file
        — is never touched, and neither is a :file:`conf.py` carrying
        configuration of its own. Everything written is derived from
        :file:`technote.toml`, so a technote that has been renamed or moved
        gets tooling that agrees with its current metadata.

        Parameters
        ----------
        ignore_files
            Paths, from the technote root, to leave alone. These are files a
            technote has customized on purpose.
        dry_run
            If `True`, report what would change without writing anything.

        Returns
        -------
        list of FileOutcome
            One outcome per standard file, in the order they are reported.

        Raises
        ------
        ValueError
            Raised if technote.toml does not carry the metadata the templates
            need.
        """
        context = self._template_context()
        ignored = {_normalize_path(name) for name in ignore_files}

        outcomes = [
            self._refresh_file(
                rel_path, template, context, ignored, dry_run=dry_run
            )
            for rel_path, template in TOOLING_TEMPLATES.items()
        ]
        outcomes.append(
            self._refresh_conf_py(context, ignored, dry_run=dry_run)
        )
        return outcomes

    def _refresh_file(
        self,
        rel_path: str,
        template_name: str,
        context: dict[str, Any],
        ignored: set[str],
        *,
        dry_run: bool,
    ) -> FileOutcome:
        """Bring one templated file up to date."""
        if rel_path in ignored:
            return FileOutcome(rel_path, UpdateStatus.skipped)

        content = self._templates.render(name=template_name, context=context)
        path = self.root_dir / rel_path
        if path.is_file() and path.read_text() == content:
            return FileOutcome(rel_path, UpdateStatus.unchanged)

        if not dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        return FileOutcome(rel_path, UpdateStatus.updated)

    def _refresh_conf_py(
        self,
        context: dict[str, Any],
        ignored: set[str],
        *,
        dry_run: bool,
    ) -> FileOutcome:
        """Bring conf.py up to date, unless the technote has extended it.

        :file:`conf.py` is Sphinx configuration a technote may legitimately
        own, so it is rewritten only when it holds something Documenteer
        generated. A technote that has added anything to it keeps what it
        wrote, and is told the file was left alone.
        """
        path = self.root_dir / CONF_PY_PATH
        if (
            CONF_PY_PATH not in ignored
            and path.is_file()
            and path.read_text() not in TEMPLATE_CONF_PY_CONTENTS
        ):
            return FileOutcome(CONF_PY_PATH, UpdateStatus.differs)

        return self._refresh_file(
            CONF_PY_PATH, CONF_PY_TEMPLATE, context, ignored, dry_run=dry_run
        )

    def _template_context(self) -> dict[str, Any]:
        """Build the template context from technote.toml.

        The templates were written for the legacy conversion, which had a
        :file:`metadata.yaml` to read from; a modern technote's equivalents
        all live in :file:`technote.toml`, so the same context is assembled
        from the handle, the repository URL, and the canonical URL it
        declares.
        """
        toml_path = self.root_dir / "technote.toml"
        toml_file = TechnoteTomlFile.open(toml_path)
        technote_table = toml_file.data.get("technote")
        if not isinstance(technote_table, dict):
            # A ValueError, not a TypeError, because this is a file the
            # writer can fix rather than a call made with the wrong type:
            # the command turns it into a message about technote.toml.
            raise ValueError(  # noqa: TRY004
                f"{toml_path} has no [technote] table."
            )

        handle = technote_table.get("id")
        if not isinstance(handle, str) or "-" not in handle:
            raise ValueError(
                f"{toml_path} does not declare the technote's handle as "
                f'[technote] id (for example, id = "SQR-000").'
            )
        series, _, serial_number = handle.rpartition("-")
        series_id = technote_table.get("series_id")
        if isinstance(series_id, str) and series_id:
            series = series_id

        github_url = technote_table.get("github_url")
        github_namespace = (
            _github_namespace(github_url)
            if isinstance(github_url, str)
            else ""
        )

        canonical_url = technote_table.get("canonical_url")
        if not isinstance(canonical_url, str) or not canonical_url:
            canonical_url = f"https://{handle.lower()}.lsst.io/"

        return {
            "cookiecutter": {
                "series": series,
                "serial_number": serial_number,
                "url": canonical_url,
                "github_namespace": github_namespace,
            }
        }

    def convert_legacy(self, *, author_ids: list[str]) -> None:
        """Convert a legacy metadata.yaml technote to technote.toml."""
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
        templates = self._templates

        github_namespace = _github_namespace(original_metadata["github_url"])

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
