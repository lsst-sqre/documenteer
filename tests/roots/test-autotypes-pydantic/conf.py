# Sphinx configuration for testing documenteer.ext.autotypes' handling of
# non-field members on autodoc-pydantic model pages.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    # autodoc-pydantic's model documenter is a legacy class-based
    # documenter, the API Sphinx 9 stopped populating with its own
    # built-in documenters.
    "sphinxcontrib.autodoc_pydantic",
    "documenteer.ext.autotypes",
]

project = "Autotypes Pydantic Test"
html_theme = "basic"
exclude_patterns = ["_build"]
default_role = "py:obj"
