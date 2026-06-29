"""Back-compat shim for the vendored ``documenteer.ext.diagrams`` extension.

Documenteer historically depended on the unmaintained ``sphinx-diagrams``
package. That extension is now vendored as ``documenteer.ext.diagrams``. This
shim keeps legacy imports (``from sphinx_diagrams import SphinxDiagram``) and
``extensions = ["sphinx_diagrams"]`` working, including inside the subprocess
that renders diagram scripts.
"""

from documenteer.ext.diagrams import SphinxDiagram, setup

__all__ = ["SphinxDiagram", "setup"]
