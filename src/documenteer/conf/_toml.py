"""Parses a documenteer.toml configuration file to support documenteer's
configuration preset modules.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Optional

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

from pathlib import Path

from pydantic import BaseModel, Field, HttpUrl
from sphinx.errors import ConfigError

__all__ = ["ProjectModel", "ConfigRoot", "DocumenteerConfig"]


class ProjectModel(BaseModel):
    """Model for the project table in the documenteer.toml file."""

    title: str = Field(
        description=(
            "Name of the project, used as titles throughout the documentation "
            "site."
        )
    )

    canonical_url: Optional[HttpUrl] = Field(
        description="Canonical root URL for this site."
    )


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
        conf = ConfigRoot.parse_obj(tomllib.loads(toml_content))
        return cls(conf)

    @property
    def project(self) -> str:
        """Project title."""
        return self.conf.project.title

    @property
    def canonical_url(self) -> Optional[str]:
        """Canonical root URL for the site, if set."""
        if self.conf.project.canonical_url is not None:
            return str(self.conf.project.canonical_url)
        return None
