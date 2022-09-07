from documenteer.conf.guide import *

# Warnings to ignore
nitpick_ignore = [
    # This link to the base pybtex still never resolves because it is not
    # in pybtex's intersphinx'd API reference.
    ("py:class", "pybtex.style.formatting.plain.Style"),
]

# Automodapi
# https://sphinx-automodapi.readthedocs.io/en/latest/automodapi.html
automodapi_toctreedirnm = "dev/api/contents"
