# Sphinx configuration for testing documenteer.ext.autotypes' handling of
# references that resolve to this project's own private module paths.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "documenteer.ext.autotypes",
]

project = "Autotypes Private Test"
html_theme = "basic"
exclude_patterns = ["_build"]
nitpicky = True
default_role = "py:obj"
