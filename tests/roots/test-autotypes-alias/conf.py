# Sphinx configuration for testing documenteer.ext.autotypes' handling of
# bare references to plain-assignment type aliases defined in packages that
# share this project's top-level root without being documented by it.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "documenteer.ext.autotypes",
]

project = "Autotypes Alias Test"
html_theme = "basic"
exclude_patterns = ["_build"]
nitpicky = True
default_role = "py:obj"
