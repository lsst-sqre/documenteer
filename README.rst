.. image:: https://img.shields.io/pypi/v/documenteer.svg?style=flat-square
   :target: https://pypi.python.org/pypi/documenteer
   :alt: PyPI
.. image:: https://img.shields.io/pypi/l/documenteer.svg?style=flat-square
   :alt: MIT license
   :target: https://pypi.python.org/pypi/documenteer
.. image:: https://img.shields.io/pypi/wheel/documenteer.svg?style=flat-square
   :alt: Uses wheel
   :target: https://pypi.python.org/pypi/documenteer
.. image:: https://img.shields.io/pypi/pyversions/documenteer.svg?style=flat-square
   :alt: For Python 2.7 and 3.5+
   :target: https://pypi.python.org/pypi/documenteer

###########
Documenteer
###########

Sphinx documentation tools for `LSST Data Management <http://dm.lsst.org>`_ projects.

Installation
============

How you install Documenteer depends on the project you're using it for:

- For technical note projects: ``pip install documenteer[technote]``
- For the https://pipelines.lsst.io project: ``pip install documenteer[pipelines]``

Development
===========

Create a virtual environment with your method of choice (virtualenvwrapper or conda) and then clone or fork, and install::

   git clone https://github.com/lsst-sqre/documenteer.git
   cd documenteer
   pip install -e ".[technote,pipelines,dev]"

To make a release:

1. Update ``CHANGELOG.rst``.
2. Tag: ``git tag -s -m "X.Y.Z" vX.Y.Z``
3. Push: ``git push --tags``

`Travis <https://travis-ci.org/lsst-sqre/documenteer>`_ handles the PyPI deployment.

License and info
================

Documenteer is a project by the `Large Synoptic Survey Telescope <https://www.lsst.org>`_.

MIT licensed.
See `LICENSE <./LICENSE>`_ for details.
