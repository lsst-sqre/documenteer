[![Documentation](https://img.shields.io/badge/documenteer-lsst.io-brightgreen.svg)](https://documentation.lsst.io)
[![PyPI](https://img.shields.io/pypi/v/documenteer.svg?style=flat-square)](https://pypi.python.org/pypi/documenteer)
[![For Python 3.7+](https://img.shields.io/pypi/pyversions/documenteer.svg?style=flat-square)](https://pypi.python.org/pypi/documenteer)
[![MIT license](https://img.shields.io/pypi/l/documenteer.svg?style=flat-square)](https://pypi.python.org/pypi/documenteer)
[![CI](https://github.com/lsst-sqre/documenteer/actions/workflows/ci.yaml/badge.svg)](https://github.com/lsst-sqre/documenteer/actions/workflows/ci.yaml)
[![Weekly CI](https://github.com/lsst-sqre/documenteer/actions/workflows/ci-cron.yaml/badge.svg)](https://github.com/lsst-sqre/documenteer/actions/workflows/ci-cron.yaml)

# Documenteer

Documenteer provides tools, extensions, and configurations for Rubin Observatory's Sphinx documentation projects, including [technotes](https://developer.lsst.io/project-docs/technotes.html) and EUPS-packaged stacks (such as the [LSST Science Pipelines](https://pipelines.lsst.io)).

For more information about Documenteer, see the documentation at https://documenteer.lsst.io.

Browse the [lsst-doc-engineering](https://github.com/topics/lsst-doc-engineering) GitHub topic for more Rubin Observatory documentation engineering projects.

## Quick installation:

For technical note projects:

```sh
pip install "documenteer[technote]"
```

For the stack projects (such as the [LSST Science Pipelines](https://pipelines.lsst.io)):

```sh
pip install "documenteer[pipelines]"
```

## Features

### Configurations

Documenteer includes preset configurations for common Rubin Observatory Sphinx projects.
By using Documenteer, you can also ensure that Sphinx extensions required by these configurations are installed.

From the `conf.py` for technotes:

```py
from documenteer.conf.technote import *
```

From the `conf.py` for a stack package:

```py
from documenteer.conf.pipelinespkg import *

project = "example"
html_theme_options['logotext'] = project
html_title = project
html_short_title = project
```

From the `conf.py` for the LSST Science Pipelines documentation:

```py
from documenteer.conf.pipelines import *
```

### Command-line tools

- [package-docs]( https://documenteer.lsst.io/pipelines/package-docs-cli.html) builds documentation for individual packages in the LSST Science Pipelines
- [stack-docs](https://documenteer.lsst.io/pipelines/stack-docs-cli.html) builds documentation for entire Stacks, such as the LSST Science Pipelines
- [refresh-lsst-bib](https://developer.lsst.io/project-docs/technotes.html#using-bibliographies-in-restructuredtext-technotes) maintains Rubin Observatory's common BibTeX files in individual technote repositories

### Sphinx extensions

- Roles for linking to LSST documents and Jira tickets
- The `remote-code-block` directive
- The `module-toctree` and `package-toctree` directives for the LSST Science Pipelines documentation
- [Extensions for documenting LSST Science Pipelines tasks](https://documenteer.lsst.io/sphinxext/lssttasks.html)
- Support for LSST BibTeX files with sphinxcontrib-bibtex.
