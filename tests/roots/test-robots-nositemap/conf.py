# Basic Sphinx configuration for testing robots extension without sitemap
extensions = [
    "documenteer.ext.robots",
]

project = "Robots No Sitemap Test"
html_baseurl = "https://project.lsst.io"

# Basic theme without sitemap
html_theme = "basic"
exclude_patterns = ["_build"]
