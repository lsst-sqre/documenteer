# Basic Sphinx configuration for testing the lastmodified extension
extensions = [
    "documenteer.ext.lastmodified",
]

project = "Last Modified Test"
html_theme = "basic"
exclude_patterns = ["_build"]
