"""Configuration and execution of Doxygen at the stack level.
"""

__all__ = [
    'DoxygenConfiguration', 'preprocess_package_doxygen_conf',
    'render_doxygen_mainpage', 'run_doxygen'
]

from copy import deepcopy
import csv
from collections.abc import Iterable
from dataclasses import dataclass, field, fields
import itertools
import logging
import os
from pathlib import Path
import re
import subprocess
from typing import List, Tuple, Set, Any

from documenteer.utils import working_directory
from .pkgdiscovery import Package

_PATH_LIKE = (
    "EXAMPLE_PATH",
    "EXCLUDE",
    "INCLUDE_PATH",
    "@INCLUDE_PATH",
    "INPUT",
    "IMAGE_PATH",
    "GENERATE_TAGFILE"
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

_COMMENT_PATTERN = re.compile(r'^[ \t]*##')
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

    inputs: List[Path] = field(
        default_factory=list,
        metadata={
            'doxygen_tag': 'INPUT'
        }
    )
    """Individual paths to be input into the doxygen build.
    """

    excludes: List[Path] = field(
        default_factory=list,
        metadata={
            'doxygen_tag': 'EXCLUDE'
        }
    )
    """File or directory paths to be excluded from the inputs.
    """

    recursive: bool = field(
        default=True,
        metadata={
            'doxygen_tag': 'RECURSIVE'
        }
    )
    """Whether or not directories listed in ``inputs`` should be searched
    recursively.
    """

    file_patterns: List[str] = field(
        default_factory=lambda: ['*.h', '*.dox'],
        metadata={
            'doxygen_tag': 'FILE_PATTERNS'
        }
    )
    """File extensions to include from the directories described by
    ``inputs``.
    """

    exclude_patterns: List[str] = field(
        default_factory=list,
        metadata={
            'doxygen_tag': 'EXCLUDE_PATTERNS'
        }
    )
    """Absolute file paths that match these patterns are excluded from the
    Doxygen build.
    """

    exclude_symbols: List[str] = field(
        default_factory=list,
        metadata={
            'doxygen_tag': 'EXCLUDE_SYMBOLS'
        }
    )
    """Symbols to exclude from the Doxygen build, such as namespace, function,
    or class names.
    """

    project_name: str = field(
        default='The LSST Science Pipelines',
        metadata={
            'doxygen_tag': 'PROJECT_NAME'
        }
    )
    """Name of the Doxygen project (used in the HTML output).
    """

    project_brief: str = field(
        default='C++ API Reference',
        metadata={
            'doxygen_tag': 'PROJECT_BRIEF'
        }
    )
    """Brief description (subtile) of the project.
    """

    output_directory: Path = field(
        default_factory=lambda: Path.cwd(),
        metadata={
            'doxygen_tag': 'OUTPUT_DIRECTORY'
        }
    )
    """Directory where Doxygen output will be generated, by default.
    """

    generate_html: bool = field(
        default=False,
        metadata={
            'doxygen_tag': 'GENERATE_HTML'
        }
    )
    """Whether or not to generate HTML output.
    """

    generate_latex: bool = field(
        default=False,
        metadata={
            'doxygen_tag': 'GENERATE_LATEX'
        }
    )
    """Whether or not to generate LaTeX output.
    """

    tagfile: Path = field(
        default_factory=lambda: Path('doxygen.tag'),
        metadata={
            'doxygen_tag': 'GENERATE_TAGFILE'
        }
    )
    """Whether or not to generate LaTeX output.
    """

    generate_xml: bool = field(
        default=True,
        metadata={
            'doxygen_tag': 'GENERATE_XML'
        }
    )
    """Whether or not ot generate XML output.
    """

    html_output: Path = field(
        default_factory=lambda: Path('html'),
        metadata={
            'doxygen_tag': 'HTML_OUTPUT'
        }
    )
    """Directory where the HTML build will be put.
    """

    use_mathjax: bool = field(
        default=True,
        metadata={
            'doxygen_tag': 'USE_MATHJAX'
        }
    )
    """Enable MathJax to render math, rather than LaTeX.
    """

    mathjax_format: str = field(
        default='SVG',
        metadata={
            'doxygen_tag': 'MATHJAX_FORMAT'
        }
    )
    """Format of the MathJax output in the HTML build.
    """

    xml_output: Path = field(
        default_factory=lambda: Path('xml'),
        metadata={
            'doxygen_tag': 'XML_OUTPUT'
        }
    )
    """Directory to output XML build products into.
    """

    xml_programlisting: bool = field(
        default=False,
        metadata={
            'doxygen_tag': 'XML_PROGRAMLISTING'
        }
    )
    """Whether to include the program listing in the XML output.
    """

    create_subdirs: bool = field(
        default=False,
        metadata={
            'doxygen_tag': 'CREATE_SUBDIRS'
        }
    )
    """Whether Doxygen should create subdirectories.

    This should be NO for breathe/exhale to work.
    """

    full_path_names: bool = field(
        default=True,
        metadata={
            'doxygen_tag': 'FULL_PATH_NAMES'
        }
    )
    """Doxygen keeps the full path of each file, rather than stripping it.
    """

    strip_from_path: List[Path] = field(
        default_factory=list,
        metadata={
            'doxygen_tag': 'STRIP_FROM_PATH'
        }
    )
    """Path prefixes to strip from path names.
    """

    enable_preprocessing: bool = field(
        default=True,
        metadata={
            'doxygen_tag': 'ENABLE_PREPROCESSING'
        }
    )

    macro_expansion: bool = field(
        default=True,
        metadata={
            'doxygen_tag': 'MACRO_EXPANSION'
        }
    )

    expand_only_predef: bool = field(
        default=False,
        metadata={
            'doxygen_tag': 'EXPAND_ONLY_PREDEF'
        }
    )

    skip_function_macros: bool = field(
        default=False,
        metadata={
            'doxygen_tag': 'SKIP_FUNCTION_MACROS'
        }
    )

    def __str__(self) -> str:
        return self.render()

    def render(self) -> str:
        """Render the Doxygen configuration file.

        Returns
        -------
        config_content
            Text content of a doxygen configuration file.
        """
        lines: List[str] = []
        for tag_field in fields(self):
            tag_name = tag_field.metadata['doxygen_tag']
            value = getattr(self, tag_field.name)
            if tag_field.type == bool:
                self._render_bool(lines, tag_name, value)
            elif tag_field.type == str:
                self._render_str(lines, tag_name, value)
            elif tag_field.type == List[Path]:
                self._render_path_list(lines, tag_name, value)
            elif tag_field.type == List[str]:
                self._render_str_list(lines, tag_name, value)
            elif tag_field.type == Path:
                self._render_path(lines, tag_name, value)
        return '\n'.join(lines) + '\n'

    def _render_bool(
            self, lines: List[str], tag_name: str, value: bool) -> None:
        if value:
            line = f'{tag_name} = YES'
        else:
            line = f'{tag_name} = NO'
        lines.append(line)

    def _render_str(
            self, lines: List[str], tag_name: str, value: str) -> None:
        if value == '':
            return
        elif ' ' in value:
            line = f'{tag_name} = "{value}"'
        else:
            line = f'{tag_name} = {value}'
        lines.append(line)

    def _render_path(
            self, lines: List[str], tag_name: str, value: Path) -> None:
        line = f'{tag_name} = {value.resolve()}'
        lines.append(line)

    def _render_path_list(
            self, lines: List[str], tag_name: str, value: List[Path]) -> None:
        sep = '='
        for p in value:
            path_str = str(p.resolve())
            # Quote paths with whitespaces
            if ' ' in path_str:
                path_str = f'"{path_str}"'
            lines.append(
                f'{tag_name} {sep} {path_str}'
            )
            sep = '+='

    def _render_str_list(
            self, lines: List[str], tag_name: str, value: List[str]) -> None:
        sep = '='
        for item in value:
            lines.append(
                f'{tag_name} {sep} {item}'
            )
            sep = '+='

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
            self, other: "DoxygenConfiguration") -> "DoxygenConfiguration":
        """Append other's configuration, in place.
        """
        self._append_config(self, other)
        return self

    def _append_config(
            self,
            mutated_config: "DoxygenConfiguration",
            new_config: "DoxygenConfiguration") -> None:
        for tag_field in fields(new_config):
            attrname = tag_field.name
            new_value = getattr(new_config, attrname)
            if isinstance(new_value, Iterable) \
                    and not isinstance(new_value, str):
                # This algorithm lets us filter duplicates while preserving
                # order. The trick with typing is that seen.add does not
                # return a type, but mypy expects a boolean given the logical
                # expression.
                _existing_values = getattr(mutated_config, attrname)
                seen: Set[Any] = set()
                setattr(mutated_config, attrname, [
                    x for x in itertools.chain(_existing_values, new_value)
                    if not (x in seen or seen.add(x))]  # type: ignore
                )
            else:
                if new_value == tag_field.default:
                    continue
                else:
                    setattr(mutated_config, tag_field.name, new_value)

    @classmethod
    def from_doxygen_conf(
            cls, conf_text: str, root_dir: Path) -> "DoxygenConfiguration":
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
        doxygen_configuration
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

        These are the only tags that individual packages should need to
        configure with respect to a stack-wide Doxygen build.
        """
        # logger = logging.getLogger(__name__)

        # Filter out comment lines
        conf_text = '\n'.join(
            [_ for _ in conf_text.split('\n')
             if not _COMMENT_PATTERN.match(_)]
        )

        # Filter out blank lines
        cont_text = re.sub(r"\n+", "\n", conf_text)

        # Remove line continuations
        sep = '\a'
        conf_text = re.sub(r"\s*\\\n+\s*", sep, cont_text)

        doxygen_conf = cls()

        for entry in conf_text.split("\n"):
            try:
                name, values = DoxygenConfiguration._parse_entry(
                    entry=entry,
                    sep=sep)
            except EntryParsingError:
                continue
            if len(values) == 0:
                continue

            # Assign selected values to the Doxygen configuration
            # Only the following tags are relevant for incorporation from
            # a single package's doxygen.conf file.
            if name == 'INPUT':
                paths = DoxygenConfiguration._convert_to_paths(
                    values, root_dir)
                doxygen_conf.inputs.extend(paths)
            elif name == 'EXCLUDE':
                paths = DoxygenConfiguration._convert_to_paths(
                    values, root_dir)
                doxygen_conf.excludes.extend(paths)
            elif name == 'EXCLUDE_PATTERNS':
                doxygen_conf.exclude_patterns.extend(values)
            elif name == 'EXCLUDE_SYMBOLS':
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
                'Did not match an expected Doxygen conf line: %r', entry)
            raise EntryParsingError

        name = match.group('name')
        is_path_like = name in _PATH_LIKE  # True if config is path-like

        raw_value = match.group('value')

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
                delimiter=' ',
                quotechar='"',
                skipinitialspace=True)
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
        *, conf: DoxygenConfiguration, package: Package) -> None:
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
    dirnames = ['include']
    for path in map(lambda p: package.root_dir / p, dirnames):
        if path.is_dir():
            conf.inputs.append(path)
            conf.strip_from_path.append(path)


def render_doxygen_mainpage() -> str:
    """Render the mainpage.dox page that provides content for the Doxygen
    subsite's homepage.

    Returns
    -------
    content : `str`
        The content of ``mainpage.dox``.
    """
    template_path = Path(__file__).parent / 'data' / 'mainpage.dox'
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
    status
        The shell status code returned by the ``doxygen`` executable.
    """
    os.makedirs(root_dir, exist_ok=True)

    with working_directory(root_dir):
        conf_path = Path('doxygen.conf')
        conf_path.write_text(conf.render())
        result = subprocess.run(['doxygen', str(conf_path)])

    return result.returncode
