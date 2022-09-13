"""Parses a documenteer.toml configuration file to support documenteer's
configuration preset modules.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from email.message import Message
from typing import (
    Any,
    Dict,
    List,
    MutableMapping,
    Optional,
    Tuple,
    Union,
    cast,
)
from urllib.parse import urlparse

if sys.version_info < (3, 8):
    from importlib_metadata import PackageNotFoundError, metadata
    from importlib_metadata import version as get_version
else:
    from importlib.metadata import PackageNotFoundError, metadata
    from importlib.metadata import version as get_version

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

from pathlib import Path

from pydantic import (
    BaseModel,
    Field,
    FilePath,
    HttpUrl,
    ValidationError,
    validator,
)
from sphinx.errors import ConfigError

from ._utils import GitRepository

__all__ = ["ProjectModel", "ConfigRoot", "DocumenteerConfig"]


class PythonPackageModel(BaseModel):
    """Model for a Python package (i.e. built with pyproject.toml-compatible
    build system.
    """

    package: str = Field(description="Package name")

    documentation_url_key: str = Field(
        "Homepage",
        description=(
            "Key for the documentation URL in the pyproject.toml "
            "[project.urls] table. The corresponding URL is used for "
            "the Sphinx html_baseurl configuration, which in turns sets the "
            "canonical URL link relation on the web pages."
        ),
    )

    github_url_key: str = Field(
        "Source",
        description=(
            "Key for the documentation URL in the pyproject.toml "
            "[project.urls] table. The corresponding URL is used for "
            "as an alternative to setting [project.github_url]."
        ),
    )

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

    github_default_branch: str = Field(
        "main",
        description="The project's default development branch on GitHub.",
    )

    version: Optional[str] = Field(description="Version string.")

    python: Optional[PythonPackageModel]


class IntersphinxModel(BaseModel):
    """Model for Intersphinx configurations in documenteer.toml."""

    projects: Dict[str, HttpUrl] = Field(
        description="Mapping of projects and their URLs.", default_factory=dict
    )


class LinkCheckModel(BaseModel):
    """Model for linkcheck builder configurations in documenteer.toml."""

    ignore: List[str] = Field(
        description="Regular expressions of URLs to skip checking links",
        default_factory=list,
    )


class ThemeModel(BaseModel):
    """Model for theme configurations in documenteer.toml."""

    show_github_edit_link: bool = Field(
        True, description="Show a link to edit on GitHub if True"
    )

    header_links_before_dropdown: int = Field(
        5,
        description=(
            "Number of links in the header nav before showing a 'More' "
            "dropdown."
        ),
    )


class SphinxModel(BaseModel):
    """Model for Sphinx configurations in documenteer.toml."""

    rst_epilog_file: Optional[FilePath] = Field(
        description=(
            "Path to a reStructuredText file that is added to every source "
            "file. Use this file to define common links and substitutions."
        )
    )

    extensions: List[str] = Field(
        description="Additional Sphinx extension.", default_factory=list
    )

    nitpicky: bool = Field(
        False, description="Escalate warnings to build errors."
    )

    nitpick_ignore: List[Tuple[str, str]] = Field(
        description=(
            "Errors to ignore. First item is the type (like a role or "
            "directive) and the second is the target (like the argument to "
            "the role)."
        ),
        default_factory=list,
    )

    nitpick_ignore_regex: List[Tuple[str, str]] = Field(
        description=(
            "Same as ``nitpick_ignore``, but both type and target are "
            "interpreted as regular expressions."
        ),
        default_factory=list,
    )

    disable_primary_sidebars: Optional[List[str]] = Field(
        None,
        description=(
            "Pages that should not have a primary sidebar. Can be the page's "
            "path (without extension) or a glob of pages. By default the "
            "homepage and change logs do not have a primary sidebar."
        ),
    )

    python_api_dir: Optional[str] = Field(
        None,
        description=(
            "Directory path where the Python API reference documentation "
            "is created."
        ),
    )

    theme: ThemeModel = Field(default_factory=lambda: ThemeModel())

    intersphinx: Optional[IntersphinxModel]

    linkcheck: Optional[LinkCheckModel]


class ConfigRoot(BaseModel):
    """The root model for a documenteer.toml configuration file."""

    project: ProjectModel

    sphinx: Optional[SphinxModel] = None


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

        The URL is obtained in this order:

        1. The ``base_url`` field of the ``[project]`` table in
           documenteer.toml.
        2. From importlib.metadata if ``[project.python]`` is set in
           documenteer.toml.
        3. Default is "".
        """
        if self.conf.project.base_url is not None:
            return str(self.conf.project.base_url)
        elif self.conf.project.python is not None:
            package_name = self.conf.project.python.package
            pyproject_meta = self._get_pyproject_metadata(package_name)
            url = self._get_pyproject_url(
                pyproject_meta, self.conf.project.python.documentation_url_key
            )
            if url is None:
                return ""
            return url
        return ""

    @property
    def copyright(self) -> str:
        """The copyright statement.

        Default is ``""`` if not set.
        """
        return self.conf.project.copyright

    @property
    def github_url(self) -> Optional[str]:
        """The project's GitHub repository.

        The GitHub URL is obtained in this order:

        1. The project.github_url field in ``documenteer.toml``
        2. From importlib if the project.python table is set
        3. Default is None.
        """
        if self.conf.project.github_url is not None:
            # User explicitly set the github URL
            return self.conf.project.github_url
        elif self.conf.project.python is not None:
            package_name = self.conf.project.python.package
            pyproject_meta = self._get_pyproject_metadata(package_name)
            url = self._get_pyproject_url(
                pyproject_meta, self.conf.project.python.github_url_key
            )
            return url
        return None

    @property
    def version(self) -> Optional[str]:
        """The project's version.

        The version is obtained in this order:

        1. project.version field in ``documenteer.toml``
        2. From importlib if the project.python table is set
        3. Default is None.
        """
        if self.conf.project.version is not None:
            return self.conf.project.version
        elif self.conf.project.python is not None:
            # Via pydantic validation we know this works
            return get_version(self.conf.project.python.package)
        else:
            return None

    @property
    def rst_epilog_path(self) -> Optional[Path]:
        """Path to the user's reStructuredText epilog file, if set."""
        if self.conf.sphinx and self.conf.sphinx.rst_epilog_file is not None:
            return Path(self.conf.sphinx.rst_epilog_file)
        else:
            return None

    @property
    def rst_epilog(self) -> str:
        """Content of the user's reStructuredText epilog, or an empty string
        if not set.
        """
        if self.rst_epilog_path is None:
            return ""
        else:
            return self.rst_epilog_path.read_text()

    def _get_pyproject_metadata(self, package_name: str) -> Message:
        if sys.version_info >= (3, 10) or sys.version_info < (3, 8):
            pkg_metadata = cast(Message, metadata(package_name))
        else:
            pkg_metadata = metadata(package_name)
        return pkg_metadata

    def _get_pyproject_url(
        self, pkg_metadata: Message, label: str
    ) -> Optional[str]:
        """Get a URL from a python package's metadata.

        Label corresponds to a field under [project.urls] in project.toml.
        """
        prefix = f"{label}, "
        for key, value in pkg_metadata.items():
            if key == "Project-URL":
                if value.startswith(prefix):
                    return value[len(prefix) :]
        return None

    def append_extensions(self, extensions: List[str]) -> None:
        """Append user-configured extensions to an existing list."""
        if self.conf.sphinx:
            for new_ext in self.conf.sphinx.extensions:
                if new_ext not in extensions:
                    extensions.append(new_ext)

    def extend_intersphinx_mapping(
        self, mapping: MutableMapping[str, Tuple[str, Union[str, None]]]
    ) -> None:
        """Extend the ``intersphinx_mapping`` dictionary with configured
        projects.
        """
        if (
            self.conf.sphinx
            and self.conf.sphinx.intersphinx
            and self.conf.sphinx.intersphinx.projects
        ):
            for project, url in self.conf.sphinx.intersphinx.projects.items():
                mapping[project] = (str(url), None)

    def append_linkcheck_ignore(self, link_patterns: List[str]) -> None:
        """Append URL patterns for sphinx.linkcheck.ignore to existing
        patterns.
        """
        if self.conf.sphinx and self.conf.sphinx.linkcheck:
            link_patterns.extend(self.conf.sphinx.linkcheck.ignore)

    def append_nitpick_ignore(
        self, nitpick_ignore: List[Tuple[str, str]]
    ) -> None:
        if self.conf.sphinx and self.conf.sphinx.nitpick_ignore:
            nitpick_ignore.extend(self.conf.sphinx.nitpick_ignore)

    def append_nitpick_ignore_regex(
        self, nitpick_ignore_regex: List[Tuple[str, str]]
    ) -> None:
        if self.conf.sphinx and self.conf.sphinx.nitpick_ignore_regex:
            nitpick_ignore_regex.extend(self.conf.sphinx.nitpick_ignore_regex)

    @property
    def nitpicky(self) -> bool:
        if self.conf.sphinx:
            return self.conf.sphinx.nitpicky
        else:
            return False

    def disable_primary_sidebars(
        self, html_sidebars: MutableMapping[str, List[str]]
    ) -> None:
        if self.conf.sphinx and self.conf.sphinx.disable_primary_sidebars:
            pages = self.conf.sphinx.disable_primary_sidebars
        else:
            pages = ["index"]  # default
        html_sidebars.update({name: list() for name in pages})

    @property
    def automodapi_toctreedirm(self) -> str:
        if self.conf.sphinx and self.conf.sphinx.python_api_dir is not None:
            return self.conf.sphinx.python_api_dir
        else:
            return "api"

    def set_edit_on_github(
        self,
        html_theme_options: MutableMapping[str, Any],
        html_context: MutableMapping[str, Any],
    ) -> None:
        """Configures the Edit on GitHub functionality, if possible."""
        if (
            self.conf.sphinx
            and self.conf.sphinx.theme.show_github_edit_link is False
        ):
            return

        if self.github_url is None:
            raise ConfigError(
                "sphinx.show_github_edit_link is True by the "
                "project.github_url is not set."
            )

        parsed_url = urlparse(self.github_url)
        path_parts = parsed_url.path.split("/")
        try:
            # first part is "/"
            github_owner = path_parts[1]
            github_repo = path_parts[2].split(".")[0]  # drop .git if present
        except IndexError:
            raise ConfigError(
                f"Could not parse GitHub repo URL: {self.github_url}"
            )

        repo = GitRepository(Path.cwd())
        try:
            # the current working directory for sphinx config is always
            # the same as the directory containing the conf.py file.
            doc_dir = str(Path.cwd().relative_to(repo.working_tree_dir))
        except ValueError:
            raise ConfigError(
                "Cannot determine the path of the documentation directory "
                "relative to the Git repository root. Set "
                "sphinx.show_github_edit_link to false if this is not a "
                "git repository."
            )

        html_theme_options["use_edit_page_button"] = True
        html_context["github_user"] = github_owner
        html_context["github_repo"] = github_repo
        html_context[
            "github_version"
        ] = self.conf.project.github_default_branch
        html_context["doc_path"] = doc_dir

    @property
    def header_links_before_dropdown(self) -> int:
        """Number of links to show in the nav head before folding extra items
        into a More dropdown.
        """
        if self.conf.sphinx:
            return self.conf.sphinx.theme.header_links_before_dropdown
        else:
            return 5
