[![Documentation](https://img.shields.io/badge/documenteer-lsst.io-brightgreen.svg)](https://documenteer.lsst.io)
[![PyPI](https://img.shields.io/pypi/v/documenteer.svg?style=flat-square)](https://pypi.python.org/pypi/documenteer)
[![For Python 3.7+](https://img.shields.io/pypi/pyversions/documenteer.svg?style=flat-square)](https://pypi.python.org/pypi/documenteer)
[![MIT license](https://img.shields.io/pypi/l/documenteer.svg?style=flat-square)](https://pypi.python.org/pypi/documenteer)
[![CI](https://github.com/lsst-sqre/documenteer/actions/workflows/ci.yaml/badge.svg)](https://github.com/lsst-sqre/documenteer/actions/workflows/ci.yaml)
[![Weekly CI](https://github.com/lsst-sqre/documenteer/actions/workflows/ci-cron.yaml/badge.svg)](https://github.com/lsst-sqre/documenteer/actions/workflows/ci-cron.yaml)

# Documenteer

Documenteer provides tools, extensions, and configurations for Rubin Observatory's Sphinx documentation projects, [user guides](https://documenteer.lsst.io/guides/index.html), [technotes](https://developer.lsst.io/project-docs/technotes.html) and EUPS-packaged stacks (such as the [LSST Science Pipelines](https://pipelines.lsst.io)).

For more information about Documenteer, see the documentation at https://documenteer.lsst.io.

Browse the [lsst-doc-engineering](https://github.com/topics/lsst-doc-engineering) GitHub topic for more Rubin Observatory documentation engineering projects.

## Quick installation:

For [user guides](https://documenteer.lsst.io/guides/index.html):

```sh
pip install "documenteer[guide]"
```

For [technical note projects](https://documenteer.lsst.io/technotes/index.html):

```sh
pip install "documenteer[technote]"
```

For the [stack projects](https://documenteer.lsst.io/pipelines/index.html) (such as the [LSST Science Pipelines](https://pipelines.lsst.io)):

```sh
pip install "documenteer[pipelines]"
```
