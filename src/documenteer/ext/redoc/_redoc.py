"""Embed a Redoc site into the Sphinx documentation."""

# Adapted from https://github.com/sphinx-contrib/redoc and updated to work with
# current versions of Sphinx and Python.
#
# Original
# (c) 2017 by Ihor Kalnytskyi.
# BSD, see LICENSE for details.

import json
from collections.abc import Generator
from pathlib import Path
from typing import Any

import jinja2
import yaml
from pydantic import BaseModel, ConfigDict, Field
from sphinx.application import Sphinx

from ...version import __version__

__all__ = ["setup"]

_HERE = Path(__file__).parent.resolve()


class RedocOpts(BaseModel):
    """Model for Redoc configuration options.

    `See the Redoc documentation for details on these options.
    <https://redocly.com/docs/redoc/config>`__.
    """

    lazy_rendering: bool = Field(default=False, alias="lazy-rendering")
    suppress_warnings: bool = Field(default=False, alias="suppress-warnings")
    hide_hostname: bool = Field(default=False, alias="hide-hostname")
    required_props_first: bool = Field(
        default=False, alias="required-props-first"
    )
    no_auto_auth: bool = Field(default=False, alias="no-auto-auth")
    path_in_middle_panel: bool = Field(
        default=False, alias="path-in-middle-panel"
    )
    hide_loading: bool = Field(default=False, alias="hide-loading")
    native_scrollbars: bool = Field(default=False, alias="native-scrollbars")
    untrusted_spec: bool = Field(default=False, alias="untrusted-spec")
    expand_responses: list[str] = Field(
        default_factory=list, alias="expand-responses"
    )

    model_config = ConfigDict(populate_by_name=True)


class RedocConfig(BaseModel):
    """Model for a single Redoc configuration item in a conf.py.

    Each RedocConfig item corresponds to a single Redoc page in the Sphinx
    documentation.
    """

    name: str = Field(default="API documentation")
    page: str = Field(..., description="Output page name")
    spec_path: str = Field(..., description="Path to OpenAPI spec file")
    template: str | None = Field(
        default=None, description="Custom template path"
    )
    opts: RedocOpts = Field(default_factory=RedocOpts)

    @classmethod
    def parse_config_list(
        cls, config: list[dict[str, Any]]
    ) -> list["RedocConfig"]:
        """Parse a list of configuration dictionaries."""
        return [cls.model_validate(item) for item in config]


def render(
    app: Sphinx,
) -> Generator[tuple[str, dict[str, Any], jinja2.Template], None, None]:
    """Render Redoc pages in the html-collect-pages event."""
    try:
        # Parse and validate the configuration using Pydantic
        config_items = RedocConfig.parse_config_list(app.config.redoc)
    except Exception as exc:
        raise ValueError(
            f"Improper configuration for documenteer.ext.redoc: {exc}"
        ) from exc

    for config_item in config_items:
        if config_item.template:
            # Template from user configuration
            template_path = Path(app.confdir) / config_item.template
        else:
            # Default template
            template_path = (
                Path(__file__).parent / "assets" / "redoc.html.jinja2"
            )

        with template_path.open(encoding="utf-8") as f:
            template = jinja2.Template(f.read())

        # Create template context from the Pydantic model
        ctx = config_item.model_dump(by_alias=True)
        ctx["redoc_version"] = app.config.redoc_version

        # Parse & dump the spec to have it as properly formatted json
        specfile = Path(app.confdir) / config_item.spec_path
        with specfile.open(encoding="utf-8") as spec_fp:
            try:
                spec_contents = yaml.safe_load(spec_fp)
            except ValueError as ver:
                raise ValueError(
                    f"Cannot parse spec {config_item.spec_path!r}: {ver}"
                ) from ver

            ctx["spec"] = json.dumps(spec_contents)

        # Yield the docname, Jinja context, and Jinja template to allow
        # Sphinx to render the page.
        yield config_item.page, ctx, template


def setup(app: Sphinx) -> dict[str, Any]:
    # redoc is the list of RedocConfig items
    app.add_config_value("redoc", [], "html")
    app.add_config_value("redoc_version", "v2.5.0", "html")

    app.connect("html-collect-pages", render)

    version = __version__
    return {"version": version, "parallel_read_safe": True}
