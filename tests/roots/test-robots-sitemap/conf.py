# Basic Sphinx configuration for testing robots extension
extensions = [
    "sphinx_sitemap",
    "documenteer.ext.robots",
]

project = "Robots Sitemap Test"
html_baseurl = "https://project.lsst.io"

# Required for sitemap generation
html_theme = "basic"
exclude_patterns = ["_build"]
