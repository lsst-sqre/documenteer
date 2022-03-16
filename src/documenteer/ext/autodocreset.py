"""Sphinx extension to reset autodoc enhancements made by sphinx-automodapi
that may be incompatible with LSST Science Pipelines API documentation.

Specifically, the automodapi autodoc enhancement that replaces the attr
getter for ``type`` is incompatible with pybind11 static properties. This
extension should be used *after* `sphinx_automodapi.automodapi` to
reset the autodoc attr getter for ``type`` to the one built into autodoc.
"""

from typing import TYPE_CHECKING, Any, Dict

from ..version import __version__

if TYPE_CHECKING:
    import sphinx.application


def setup(app: "sphinx.application.Sphinx") -> Dict[str, Any]:
    """Set up the ``documenteer.ext.autodocreset`` extension."""
    app.add_autodoc_attrgetter(type, getattr)

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
