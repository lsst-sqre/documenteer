# Sphinx configuration for testing documenteer.ext.autotypes
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinxcontrib.autodoc_pydantic",
    "sphinx_automodapi.automodapi",
    "documenteer.ext.autotypes",
]

project = "Autotypes Test"
html_theme = "basic"
exclude_patterns = ["_build", "_templates"]
nitpicky = True
automodapi_toctreedirnm = "api"
default_role = "py:obj"
