# Sphinx configuration for testing documenteer.ext.autotypes' handling of
# bare references in docstrings inherited from external base classes.
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "documenteer.ext.autotypes",
]

project = "Autotypes Inherited Test"
html_theme = "basic"
exclude_patterns = ["_build"]
nitpicky = True
default_role = "py:obj"


def _write_stub_inventory() -> str:
    """Write an inventory for the "external" ``extpkg`` project.

    Both ``extpkg.Formatter`` and ``extpkg.Packer`` publish a
    ``to_bytes`` method, so the terminal name is ambiguous across the
    inventory and the bare reference can only resolve through the
    fully-qualified name rebuilt from the documented class's MRO.
    """
    path = Path(__file__).parent / "extpkg.inv"
    header = (
        "# Sphinx inventory version 2\n"
        "# Project: extpkg\n"
        "# Version: 1.0\n"
        "# The remainder of this file is compressed using zlib.\n"
    ).encode()
    body = (
        "extpkg.Formatter py:class 1 formatter.html#extpkg.Formatter -\n"
        "extpkg.Formatter.to_bytes py:method 1 "
        "formatter.html#extpkg.Formatter.to_bytes -\n"
        "extpkg.Packer.to_bytes py:method 1 "
        "packer.html#extpkg.Packer.to_bytes -\n"
    ).encode()
    path.write_bytes(header + zlib.compress(body, 9))
    return str(path)


# The test that exercises the unlinked-literal degrade overrides this
# mapping with an empty one, so the same source builds both ways.
intersphinx_mapping = {
    "extpkg": ("https://extpkg.example.com/", _write_stub_inventory()),
}
