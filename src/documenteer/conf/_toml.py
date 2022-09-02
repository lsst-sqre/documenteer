"""Parses a documenteer.toml configuration file to support documenteer's
configuration preset modules.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Optional

if sys.version_info < (3, 8):
    from importlib_metadata import PackageNotFoundError
    from importlib_metadata import version as get_version
else:
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as get_version

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

from pathlib import Path

from pydantic import BaseModel, Field, HttpUrl, ValidationError, validator
from sphinx.errors import ConfigError

__all__ = ["ProjectModel", "ConfigRoot", "DocumenteerConfig"]


class PythonPackageModel(BaseModel):
    """Model for a Python package (i.e. built with pyproject.toml-compatible
    build system.
    """

    package: str = Field(description="Package name")

    @validator("package")
    def validate_package(cls, v: str) -> str:
        """Ensure the package is importable."""
        try:
            get_version(v)
        except PackageNotFoundError:
            raise ValueError(f"The package {v!r} is not importable.")
        return v


class ProjectModel(BaseModel):
    """Model for the project table in the documenteer.toml file."""

    title: str = Field(
        description=(
            "Name of the project, used as titles throughout the documentation "
            "site."
        )
    )

    base_url: Optional[HttpUrl] = Field(
        description="Canonical URL of the site's root page."
    )

    copyright: str = Field(
        "",
        description="Copyright statement, without a 'copyright' prefix word.",
    )

    github_url: Optional[HttpUrl] = Field(
        description="The URL of the project's GitHub repository."
    )

    version: Optional[str] = Field(description="Version string.")

    python: Optional[PythonPackageModel]


class ConfigRoot(BaseModel):
    """The root model for a documenteer.toml configuration file."""

    project: ProjectModel


@dataclass
class DocumenteerConfig:
    """Configuration from a documenteer.toml file."""

    conf: ConfigRoot

    @classmethod
    def find_and_load(cls) -> DocumenteerConfig:
        path = Path("documenteer.toml")
        if not path.is_file:
            raise ConfigError("Cannot find the documenteer.toml file.")
        return cls.load(path.read_text())

    @classmethod
    def load(cls, toml_content: str) -> DocumenteerConfig:
        try:
            conf = ConfigRoot.parse_obj(tomllib.loads(toml_content))
        except ValidationError as e:
            message = (
                f"Syntax or validation issue in documenteer.toml:\n\n"
                f"{str(e)}"
            )
            raise ConfigError(message)
        return cls(conf)

    @property
    def project(self) -> str:
        """Project title."""
        return self.conf.project.title

    @property
    def base_url(self) -> str:
        """Base root URL for the site.

        Default is ``""`` if not set.
        """
        if self.conf.project.base_url is not None:
            return str(self.conf.project.base_url)
        return ""

    @property
    def copyright(self) -> str:
        """The copyright statement.

        Default is ``""`` if not set.
        """
        return self.conf.project.copyright

    @property
    def github_url(self) -> Optional[str]:
        """The project's GitHub repository."""
        return self.conf.project.github_url

    @property
    def version(self) -> Optional[str]:
        """The project's version.

        If the python package is set, the version is obtained via
        ``importlib``. Otherwise, the version is obtained from the
        ``project.version`` field in ``documenteer.toml``.
        """
        if self.conf.project.python is not None:
            # Via pydantic validation we know this works
            return get_version(self.conf.project.python.package)
        elif self.conf.project.version is not None:
            return self.conf.project.version
        else:
            return None
