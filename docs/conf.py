from documenteer.conf.guide import *

# Intersphinx

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "requests": ("https://requests.readthedocs.io/en/latest/", None),
    "developer": ("https://developer.lsst.io/", None),
    "pybtex": ("https://docs.pybtex.org/", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
}

# Warnings to ignore
nitpick_ignore = [
    # This link to the base pybtex still never resolves because it is not
    # in pybtex's intersphinx'd API reference.
    ("py:class", "pybtex.style.formatting.plain.Style"),
]

# Automodapi
# https://sphinx-automodapi.readthedocs.io/en/latest/automodapi.html
automodapi_toctreedirnm = "dev/api/contents"

# ReStructuredText epilog for common links/substitutions =====================
rst_epilog = """

.. _conda-forge: https://conda-forge.org
.. _conda: https://conda.io/en/latest/index.html
"""
