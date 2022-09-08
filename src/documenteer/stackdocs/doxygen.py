"""Configuration and execution of Doxygen at the stack level.
"""

__all__ = [
    "DoxygenConfiguration",
    "preprocess_package_doxygen_conf",
    "render_doxygen_mainpage",
    "get_doxygen_default_conf_path",
    "get_cpp_reference_tagfile_path",
    "run_doxygen",
]

import csv
import itertools
import logging
import os
import re
import subprocess
from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, List, Optional, Set, Tuple

from documenteer.utils import working_directory

from .pkgdiscovery import Package

_PATH_LIKE = (
    "EXAMPLE_PATH",
    "EXCLUDE",
    "INCLUDE_PATH",
    "@INCLUDE_PATH",
    "INPUT",
    "IMAGE_PATH",
    "GENERATE_TAGFILE",
)
"""Names of path-like Doxygen configuration tags.
"""

_BLANK_LINE_PATTERN = re.compile(r"^\s*$")
"""Regular expression for a blank line in a Doxygen configuration file.
"""

_CONFIG_PATTERN = re.compile(
    # Configuration name
    r"^\s*(?P<name>\S+)"
    # Assignment operator
    r"\s*\+?=\s*"
    # Configuration value
    r"(?P<value>.*)"
)
"""Regular expression for a Doxygen configuration file.
"""

_COMMENT_PATTERN = re.compile(r"^[ \t]*##")
"""Regular expression for comment lines in a Doxygen configuration file.
"""


@dataclass
class DoxygenConfiguration:
    """A restricted Doxygen configuration.

    Rather than accomodating arbitrary Doxygen configurations, this class
    maintains the key configurations that are required for a Doxygen build
    that is intended to be incorporated into a Sphinx build. As such, this
    configuration file may ignore some configuration values when parsing a
    raw configuration file.

    Notes
    -----
    See http://www.doxygen.nl/manual/config.html for more details about
    Doxygen configurations.
    """

    include_paths: List[Path] = field(default_factory=list)
    """Paths to other Doxygen configuration files.

    This attribute is rendered as both the ``@INCLUDE_PATH`` and ``INCLUDE``
    doxygen configurations.
    """

    inputs: List[Path] = field(
        default_factory=list, metadata={"doxygen_tag": "INPUT"}
    )
    """Individual paths to be input into the doxygen build.
    """

    image_paths: List[Path] = field(
        default_factory=list, metadata={"doxygen_tag": "IMAGE_PATH"}
    )
    """Paths that contain images."""

    excludes: List[Path] = field(
        default_factory=list, metadata={"doxygen_tag": "EXCLUDE"}
    )
    """File or directory paths to be excluded from the inputs.
    """

    recursive: bool = field(
        default=True, metadata={"doxygen_tag": "RECURSIVE"}
    )
    """Whether or not directories listed in ``inputs`` should be searched
    recursively.
    """

    file_patterns: List[str] = field(
        default_factory=lambda: [".cc", "*.h", "*.dox"],
        metadata={"doxygen_tag": "FILE_PATTERNS"},
    )
    """File extensions to include from the directories described by
    ``inputs``.
    """

    exclude_patterns: List[str] = field(
        default_factory=lambda: ["*/.git", "*/.sconf_temp", "*/python/*.cc"],
        metadata={"doxygen_tag": "EXCLUDE_PATTERNS"},
    )
    """Absolute file paths that match these patterns are excluded from the
    Doxygen build.

    Pybind11 wrappers are excluded because Doxygen doesn't handle them
    correctly.
    """

    exclude_symbols: List[str] = field(
        default_factory=list, metadata={"doxygen_tag": "EXCLUDE_SYMBOLS"}
    )
    """Symbols to exclude from the Doxygen build, such as namespace, function,
    or class names.
    """

    project_name: str = field(
        default="The LSST Science Pipelines",
        metadata={"doxygen_tag": "PROJECT_NAME"},
    )
    """Name of the Doxygen project (used in the HTML output).
    """

    project_brief: str = field(
        default="C++ API Reference", metadata={"doxygen_tag": "PROJECT_BRIEF"}
    )
    """Brief description (subtile) of the project.
    """

    output_directory: Path = field(
        default_factory=lambda: Path.cwd(),
        metadata={"doxygen_tag": "OUTPUT_DIRECTORY"},
    )
    """Directory where Doxygen output will be generated, by default.
    """

    generate_html: bool = field(
        default=True, metadata={"doxygen_tag": "GENERATE_HTML"}
    )
    """Whether or not to generate HTML output.
    """

    generate_latex: bool = field(
        default=False, metadata={"doxygen_tag": "GENERATE_LATEX"}
    )
    """Whether or not to generate LaTeX output.
    """

    tagfile: Path = field(
        default_factory=lambda: Path("doxygen.tag"),
        metadata={"doxygen_tag": "GENERATE_TAGFILE"},
    )
    """Whether or not to generate LaTeX output.
    """

    tagfiles: List[str] = field(
        default_factory=lambda: [
            f"{get_cpp_reference_tagfile_path().resolve()}"
            "=http://en.cppreference.com/w/"
        ],
        metadata={"doxygen_tag": "TAGFILES"},
    )
    """The TAGFILES tag can be used to specify one or more tag files.

    For each tag file the location of the external documentation should be
    added. The format of a tag file without this location is as follows:
    TAGFILES = file1 file2 ... Adding location for the tag files is done as
    follows: TAGFILES = file1=loc1 "file2 = loc2" ... where loc1 and loc2 can
    be relative or absolute paths or URLs. See the section "Linking to external
    documentation" for more information about the use of tag files. Note: Each
    tag file must have a unique name (where the name does NOT include the
    path). If a tag file is not located in the directory in which doxygen is
    run, you must also specify the path to the tagfile here.
    """

    generate_xml: bool = field(
        default=True, metadata={"doxygen_tag": "GENERATE_XML"}
    )
    """Whether or not ot generate XML output.
    """

    html_output: Path = field(
        default_factory=lambda: Path("html"),
        metadata={"doxygen_tag": "HTML_OUTPUT"},
    )
    """Directory where the HTML build will be put.
    """

    use_mathjax: bool = field(
        default=True, metadata={"doxygen_tag": "USE_MATHJAX"}
    )
    """Enable MathJax to render math, rather than LaTeX.
    """

    mathjax_format: str = field(
        default="HTML-CSS", metadata={"doxygen_tag": "MATHJAX_FORMAT"}
    )
    """Format of the MathJax output in the HTML build.
    """

    mathjax_relpath: str = field(
        default="https://cdn.jsdelivr.net/npm/mathjax@2",
        metadata={"doxygen_tag": "MATHJAX_RELPATH"},
    )
    """Relative path or URL to the MathJax bundle."""

    xml_output: Path = field(
        default_factory=lambda: Path("xml"),
        metadata={"doxygen_tag": "XML_OUTPUT"},
    )
    """Directory to output XML build products into.
    """

    xml_programlisting: bool = field(
        default=False, metadata={"doxygen_tag": "XML_PROGRAMLISTING"}
    )
    """Whether to include the program listing in the XML output.
    """

    create_subdirs: bool = field(
        default=False, metadata={"doxygen_tag": "CREATE_SUBDIRS"}
    )
    """Whether Doxygen should create subdirectories.

    This should be NO for breathe/exhale to work.
    """

    full_path_names: bool = field(
        default=True, metadata={"doxygen_tag": "FULL_PATH_NAMES"}
    )
    """Doxygen keeps the full path of each file, rather than stripping it.
    """

    strip_from_path: List[Path] = field(
        default_factory=list, metadata={"doxygen_tag": "STRIP_FROM_PATH"}
    )
    """Path prefixes to strip from path names.
    """

    quiet: bool = field(default=True, metadata={"doxygen_tag": "QUIET"})
    """Turn off messages generated to standard output by Doxygen.
    """

    warnings: bool = field(default=True, metadata={"doxygen_tag": "WARNINGS"})
    """Enable warnings printed to standard error."""

    warn_if_undocumented: bool = field(
        default=True, metadata={"doxygen_tag": "WARN_IF_UNDOCUMENTED"}
    )
    """Warn about undocumented members.

    If EXTRACT_ALL is set to YES then this flag will automatically be disabled.
    """

    warn_if_doc_error: bool = field(
        default=True, metadata={"doxygen_tag": "WARN_IF_DOC_ERROR"}
    )
    """Warn about potential errors in the documentation."""

    warn_no_paramdoc: bool = field(
        default=False, metadata={"doxygen_tag": "WARN_NO_PARAMDOC"}
    )
    """Warn about functions that are documented but don't have documentation
    for their parameters or return value.

    If set to NO, doxygen will only warn about wrong or incomplete
    parameter documentation, but not about the absence of documentation.
    """

    warn_as_error: bool = field(
        default=False, metadata={"doxygen_tag": "WARN_AS_ERROR"}
    )
    """Treat warnings are errors."""

    warn_format: str = field(
        default="$file:$line: $text", metadata={"doxygen_tag": "WARN_FORMAT"}
    )
    """Format for warning and error messages."""

    warn_logfile: Optional[Path] = field(
        default=None, metadata={"doxygen_tag": "WARN_LOGFILE"}
    )
    """Print errors and warnings to a log file.

    If left blank the output is written to standard error (stderr).
    """

    def __str__(self) -> str:
        return self.render()

    def render(self) -> str:
        """Render the Doxygen configuration file.

        Returns
        -------
        config_content : `str`
            Text content of a doxygen configuration file.
        """
        lines: List[str] = []

        # Handle @INCLUDE_PATH and @INCLUDE as a special case
        self._render_include(lines)

        for tag_field in fields(self):
            if "doxygen_tag" not in tag_field.metadata:
                continue
            tag_name = tag_field.metadata["doxygen_tag"]
            value = getattr(self, tag_field.name)
            if tag_field.type == bool:
                self._render_bool(lines, tag_name, value)
            elif tag_field.type == str:
                self._render_str(lines, tag_name, value)
            elif tag_field.type == int:
                self._render_int(lines, tag_name, value)
            elif tag_field.type == List[Path]:
                self._render_path_list(lines, tag_name, value)
            elif tag_field.type == List[str]:
                self._render_str_list(lines, tag_name, value)
            elif tag_field.type == Path or tag_field.type == Optional[Path]:
                self._render_path(lines, tag_name, value)
        return "\n".join(lines) + "\n"

    def _render_include(self, lines: List[str]) -> None:
        if self.include_paths:
            # All directory components
            include_dirs = list(
                set(
                    [
                        str(p.parent.resolve())
                        for p in self.include_paths
                        if (p.is_file() and p.exists())
                    ]
                )
            )
            # All name components
            include_names = list(
                set(
                    [
                        str(p.name)
                        for p in self.include_paths
                        if (p.is_file() and p.exists())
                    ]
                )
            )

            lines.append(f"@INCLUDE_PATH = {' '.join(include_dirs)}")
            lines.append(f"@INCLUDE = {' '.join(include_names)}")

    def _render_bool(
        self, lines: List[str], tag_name: str, value: bool
    ) -> None:
        if value:
            line = f"{tag_name} = YES"
        else:
            line = f"{tag_name} = NO"
        lines.append(line)

    def _render_int(self, lines: List[str], tag_name: str, value: int) -> None:
        line = f"{tag_name} = {value}"
        lines.append(line)

    def _render_str(self, lines: List[str], tag_name: str, value: str) -> None:
        if value == "":
            return
        elif " " in value:
            line = f'{tag_name} = "{value}"'
        else:
            line = f"{tag_name} = {value}"
        lines.append(line)

    def _render_path(
        self, lines: List[str], tag_name: str, value: Optional[Path]
    ) -> None:
        if value:
            line = f"{tag_name} = {value.resolve()}"
            lines.append(line)

    def _render_path_list(
        self, lines: List[str], tag_name: str, value: List[Path]
    ) -> None:
        sep = "="
        for p in value:
            path_str = str(p.resolve())
            # Quote paths with whitespaces
            if " " in path_str:
                path_str = f'"{path_str}"'
            lines.append(f"{tag_name} {sep} {path_str}")
            sep = "+="

    def _render_str_list(
        self, lines: List[str], tag_name: str, value: List[str]
    ) -> None:
        sep = "="
        for item in value:
            lines.append(f"{tag_name} {sep} {item}")
            sep = "+="

    def __add__(self, other: "DoxygenConfiguration") -> "DoxygenConfiguration":
        """Append other's configurations to this configuration, yielding a
        new configuration.

        The behavior for adding configurations:

        - If a tag is single value, then the value from `other` replaces the
          value from this configuration (unless the value is a default).
        - If a tag is a sequence of values, then the items from `other` are
          appended after the items from this configuration.
        """
        new_config: "DoxygenConfiguration" = deepcopy(self)
        self._append_config(new_config, other)
        return new_config

    def __iadd__(
        self, other: "DoxygenConfiguration"
    ) -> "DoxygenConfiguration":
        """Append other's configuration, in place."""
        self._append_config(self, other)
        return self

    def _append_config(
        self,
        mutated_config: "DoxygenConfiguration",
        new_config: "DoxygenConfiguration",
    ) -> None:
        for tag_field in fields(new_config):
            attrname = tag_field.name
            new_value = getattr(new_config, attrname)
            if isinstance(new_value, Iterable) and not isinstance(
                new_value, str
            ):
                # This algorithm lets us filter duplicates while preserving
                # order. The trick with typing is that seen.add does not
                # return a type, but mypy expects a boolean given the logical
                # expression.
                _existing_values = getattr(mutated_config, attrname)
                seen: Set[Any] = set()
                setattr(
                    mutated_config,
                    attrname,
                    [
                        x
                        for x in itertools.chain(_existing_values, new_value)
                        if not (x in seen or seen.add(x))  # type: ignore
                    ],
                )
            else:
                if new_value == tag_field.default:
                    continue
                else:
                    setattr(mutated_config, tag_field.name, new_value)

    @classmethod
    def from_doxygen_conf(
        cls, conf_text: str, root_dir: Path
    ) -> "DoxygenConfiguration":
        """Create a new DoxygenConfiguration from the the content of a
        ``doxygen.conf`` or ``doxygen.conf.in`` file.

        Parameters
        ----------
        conf_text
            The text content of a ``doxygen.conf`` file.
        root_dir
            Directory containing the ``doxygen.conf`` file. This directory
            path is used to resolve any relative paths within the configuration
            file.

        Returns
        -------
        doxygen_configuration : `DoxygenConfiguration`
            A DoxygenConfiguration instance populated with configurations
            parsed from ``doxygen_conf``.

        Notes
        -----
        Only select tags from the Doxygen configuration file are parsed
        and incorporated into the DoxygenConfiguration instance:

        - INPUT
        - EXCLUDE
        - EXCLUDE_PATTERNS
        - EXCLUDE_SYMBOLS
        - IMAGE_PATH

        These are the only tags that individual packages should need to
        configure with respect to a stack-wide Doxygen build.
        """
        # logger = logging.getLogger(__name__)

        # Filter out comment lines
        conf_text = "\n".join(
            [_ for _ in conf_text.split("\n") if not _COMMENT_PATTERN.match(_)]
        )

        # Filter out blank lines
        cont_text = re.sub(r"\n+", "\n", conf_text)

        # Remove line continuations
        sep = "\a"
        conf_text = re.sub(r"\s*\\\n+\s*", sep, cont_text)

        doxygen_conf = cls()

        for entry in conf_text.split("\n"):
            try:
                name, values = DoxygenConfiguration._parse_entry(
                    entry=entry, sep=sep
                )
            except EntryParsingError:
                continue
            if len(values) == 0:
                continue

            # Assign selected values to the Doxygen configuration
            # Only the following tags are relevant for incorporation from
            # a single package's doxygen.conf file.
            if name == "INPUT":
                paths = DoxygenConfiguration._convert_to_paths(
                    values, root_dir
                )
                doxygen_conf.inputs.extend(paths)
            elif name == "EXCLUDE":
                paths = DoxygenConfiguration._convert_to_paths(
                    values, root_dir
                )
                doxygen_conf.excludes.extend(paths)
            elif name == "IMAGE_PATH":
                paths = DoxygenConfiguration._convert_to_paths(
                    values, root_dir
                )
                doxygen_conf.image_paths.extend(paths)
            elif name == "EXCLUDE_PATTERNS":
                doxygen_conf.exclude_patterns.extend(values)
            elif name == "EXCLUDE_SYMBOLS":
                doxygen_conf.exclude_symbols.extend(values)

        return doxygen_conf

    @staticmethod
    def _parse_entry(*, entry: str, sep: str) -> Tuple[str, List[str]]:
        logger = logging.getLogger(__name__)

        if _BLANK_LINE_PATTERN.match(entry):
            raise EntryParsingError

        match = _CONFIG_PATTERN.match(entry)
        if match is None:
            logger.warning(
                "Did not match an expected Doxygen conf line: %r", entry
            )
            raise EntryParsingError

        name = match.group("name")
        is_path_like = name in _PATH_LIKE  # True if config is path-like

        raw_value = match.group("value")

        # Path entries can be double-quoted if they are paths that might
        # contain spaces.
        # An entry could look like:
        #   a "b c" "d" or "a b" c d
        # Use the csv package to handle this.
        # We have to be careful to only do this processing on PATH-like
        # doxygen components.
        if is_path_like:
            # skipinitialspace handles multiple spaces between items
            csv_reader = csv.reader(
                [raw_value],
                delimiter=" ",
                quotechar='"',
                skipinitialspace=True,
            )
            value = sep.join(next(csv_reader))
        else:
            # Replace spaces with separators unless the string contains a
            # double quote
            if not re.search(r'"', raw_value):
                value = re.sub(r"\s+", sep, raw_value)
            else:
                value = raw_value

        # Remove all single and double quotes
        value = re.sub("[\"']", "", value)

        # Split based on the separator and eliminate empty items
        split_values = [v.strip() for v in value.split(sep)]
        split_values = [v for v in split_values if v]

        return name, split_values

    @staticmethod
    def _convert_to_paths(values: List[str], root_dir: Path) -> List[Path]:
        paths = []
        for v in values:
            p = Path(v)
            if p.is_absolute():
                paths.append(p)
            else:
                paths.append(root_dir.joinpath(p))
        return paths


class EntryParsingError(RuntimeError):
    """Internal exception raised when an individual line in a Doxygen
    configuration file can't be parsed, and must be skipped.
    """


def preprocess_package_doxygen_conf(
    *, conf: DoxygenConfiguration, package: Package
) -> None:
    """Preprocess a Doxygen configuration for an individual package that is
    based on a package's ``doxygen.conf.in`` file.

    This function adds paths to the ``INPUT`` and ``STRIP_FROM_PATH``
    configuration tags, and plays an equivalent role to sconsUtils to add
    configurations to the ``doxygen.conf.in`` template for a package.

    Parameters
    ----------
    conf
        A `DoxygenConfiguration` for an individual package. Most likely,
        this configuration is based on a ``doxygen.conf.in`` file, which has
        not been processed by ``sconsUtils``, and thus does not have INPUT
        configurations set.
    package
        Metadata about the package itself.

    Notes
    -----
    The only default package paths that are added to the Doxygen ``INPUT``
    configuration tag are:

    - ``include``

    The ``doc`` and ``python`` directories are handled exclusively by Sphinx.
    The ``src`` directory isn't handled because Doxygen documentation comments
    are written exclusively in header files per the LSST DM standard.
    The ``examples`` directory is also deprecated in the Sphinx regime.

    The function also addes the ``include`` directory of the package to the
    ``STRIP_FROM_PATH`` tag so that we don't publish build system-specific
    paths for header files.
    """
    dirnames = ["include", "src"]
    for path in map(lambda p: package.root_dir / p, dirnames):
        if path.is_dir():
            conf.inputs.append(path)
            conf.strip_from_path.append(path)


def get_doxygen_default_conf_path() -> Path:
    """Get the path to the doxygen configuration file included with
    Documenteer.

    Returns
    -------
    defaults_path : `pathlib.Path`
        Path the the ``doxygen.defaults.conf`` file included with Documenteer
        as a basis for Science Pipelines Doxygen configuration.
    """
    return Path(__file__).parent / "data" / "doxygen.defaults.conf"


def get_cpp_reference_tagfile_path() -> Path:
    """Get the path to the Doxygen tag file for cppreference.com that's
    included with Documenteer.

    Returns
    -------
    path : `pathlib.Path`
        Path the the ``cppreference-doxygen-web.tag.xml`` file included with
        Documenteer.
    """
    return Path(__file__).parent / "data" / "cppreference-doxygen-web.tag.xml"


def render_doxygen_mainpage() -> str:
    """Render the mainpage.dox page that provides content for the Doxygen
    subsite's homepage.

    Returns
    -------
    content : `str`
        The content of ``mainpage.dox``.
    """
    template_path = Path(__file__).parent / "data" / "mainpage.dox"
    template = template_path.read_text()
    return template


def run_doxygen(*, conf: DoxygenConfiguration, root_dir: Path) -> int:
    """Run Doxygen.

    Parameters
    ----------
    conf
        A `DoxygenConfiguration` that configures the Doxygen build.
    root_dir
        The directory that is considered the root of the Doxygen build.
        This is the directory where the Doxygen configuration is written
        as ``doxygen.conf``.

    Returns
    -------
    status : `int`
        The shell status code returned by the ``doxygen`` executable.
    """
    os.makedirs(root_dir, exist_ok=True)

    with working_directory(root_dir):
        conf_path = Path("doxygen.conf")
        conf_path.write_text(conf.render())
        result = subprocess.run(["doxygen", str(conf_path)])

    return result.returncode
