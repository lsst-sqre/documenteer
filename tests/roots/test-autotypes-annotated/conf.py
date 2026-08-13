# Sphinx configuration for testing documenteer.ext.autotypes' handling of
# the reference targets Sphinx synthesizes out of ``Annotated`` metadata.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinxcontrib.autodoc_pydantic",
    "documenteer.ext.autotypes",
]

project = "Autotypes Annotated Test"
html_theme = "basic"
exclude_patterns = ["_build"]
nitpicky = True
default_role = "py:obj"

# The field summary autodoc-pydantic puts at the top of a model page
# references each field under the model's *defining* module, while the
# models here are documented from the package that re-exports them (the
# shape that puts the metadata names out of the documented module's
# reach). Those summary references are not what this root is about.
autodoc_pydantic_model_show_field_summary = False
