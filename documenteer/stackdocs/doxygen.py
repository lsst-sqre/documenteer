"""Configuration and execution of Doxygen at the stack level.
"""

__all__ = ('DoxygenConfiguration,')

from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import List


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
    """Whether or not directories listed in `inputs` should be searched
    recursively.
    """

    file_patterns: List[str] = field(
        default_factory=lambda: ['*.h', '*.cc'],
        metadata={
            'doxygen_tag': 'FILE_PATTERNS'
        }
    )
    """File extensions to include from the directories described by `inputs`.
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

    generate_xml: bool = field(
        default=True,
        metadata={
            'doxygen_tag': 'GENERATE_XML'
        }
    )
    """Whether or not ot generate XML output.
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

    def _render_path(
            self, lines: List[str], tag_name: str, value: Path) -> None:
        line = f'{tag_name} = {value.resolve()}'
        lines.append(line)

    def _render_path_list(
            self, lines: List[str], tag_name: str, value: List[Path]) -> None:
        sep = '='
        for p in value:
            lines.append(
                f'{tag_name} {sep} {p.resolve()}'
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
