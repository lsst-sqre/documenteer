"""Interface to local Jinja templates for maintaining project repositories."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import jinja2

__all__ = ["LocalProjectTemplates"]


class LocalProjectTemplates:
    """Interface to local Jinja templates for project repositories."""

    def __init__(self) -> None:
        self._dir = Path(__file__).parent / "localtemplates"

    def get_template(self, name: str) -> jinja2.Template:
        """Get a template by name.

        Parameters
        ----------
        name
            The name of the template.

        Returns
        -------
        `jinja2.Template`
            The template object.
        """
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(self._dir))  # noqa: S701
        return env.get_template(name)

    def render(self, *, name: str, context: dict[str, Any]) -> str:
        """Render a template to the exact text `write` would put in a file.

        Rendering is separated from writing so that a caller can compare a
        template against a file that already exists — the difference between
        a file this template would change and one it would leave alone —
        without writing anything.

        Parameters
        ----------
        name
            The name of the template.
        context
            The template context.

        Returns
        -------
        str
            The rendered template, newline-terminated.
        """
        template = self.get_template(name)
        return template.render(**context) + "\n"

    def write(self, *, name: str, path: Path, context: dict[str, Any]) -> None:
        """Write a template to a file.

        Parameters
        ----------
        name
            The name of the template.
        path
            The path to write to.
        context
            The template context.
        """
        output_dir = path.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render(name=name, context=context))
