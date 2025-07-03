"""A Sphinx extension for generating the OpenAPI Spec for a
FastAPI application.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any

from sphinx.application import Sphinx
from sphinx.config import Config
from sphinx.errors import SphinxError
from sphinx.util.typing import ExtensionMetadata

from ..version import __version__

__all__ = ["generate_openapi_spec", "setup"]


def generate_openapi_spec(app: Sphinx, config: Config) -> None:
    """Generate the OpenAPI spec from a user-specified generator function.

    This is called during the ``config-inited`` Sphinx event.

    Parameters
    ----------
    app
        The Sphinx application.
    config
        The Sphinx configuration.
    """
    generator_config: dict[str, Any] | None = config[
        "documenteer_openapi_generator"
    ]
    if generator_config is None:
        return

    try:
        generator_func_config = generator_config["func"]
    except KeyError as e:
        raise SphinxError(
            "documenteer_openapi_generator must have a 'func' key "
            "specifing the function to generate the OpenAPI spec. "
            "It must have the form `module:func`."
        ) from e

    generator_func_parts = generator_func_config.split(":")
    if len(generator_func_parts) != 2:
        raise SphinxError(
            "documenteer_openapi_generator['func'] must be a string of the "
            "form 'module:func'."
        )
    generator_module_name, generator_func_name = generator_func_parts

    generator_args = generator_config.get("args", [])
    generator_kwargs = generator_config.get("kwargs", {})

    generator_module = import_module(generator_module_name)
    generator_func = getattr(generator_module, generator_func_name)
    openapi_text = generator_func(*generator_args, **generator_kwargs)

    # Write the OpenAPI spec to a file
    openapi_path = config["documenteer_openapi_path"]
    if openapi_path is None:
        raise SphinxError(
            "documenteer_openapi_path must be set to a path relative to the "
            "Sphinx source directory. It is the path to write the OpenAPI "
            "spec to."
        )

    openapi_spec_path = Path(app.confdir).joinpath(
        config["documenteer_openapi_path"]
    )
    openapi_spec_path.parent.mkdir(parents=True, exist_ok=True)
    openapi_spec_path.write_text(openapi_text)


def setup(app: Sphinx) -> ExtensionMetadata:
    """Set up the OpenAPI extension."""
    # Configuration values

    # The function to generate the OpenAPI spec.
    app.add_config_value("documenteer_openapi_generator", None, "html")

    # The path to write the OpenAPI spec, relative to the Sphinx conf.py
    # file.
    app.add_config_value("documenteer_openapi_path", None, "html")

    # Events
    app.connect("config-inited", generate_openapi_spec)

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
