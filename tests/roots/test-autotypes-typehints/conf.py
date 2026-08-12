# Sphinx configuration for testing documenteer.ext.autotypes' handling of
# module-level callable singletons under sphinx-autodoc-typehints.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    # sphinx-autodoc-typehints is the crash trigger: its
    # ``autodoc-process-signature`` handler returns a signature tuple for
    # *any* annotated callable, including a module-level ``data`` object
    # that Sphinx 9 allocates no signature slot for.
    "sphinx_autodoc_typehints",
    "documenteer.ext.autotypes",
]

project = "Autotypes Typehints Test"
html_theme = "basic"
exclude_patterns = ["_build"]
nitpicky = True
default_role = "py:obj"
