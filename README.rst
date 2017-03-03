###########
documenteer
###########

.. image:: https://img.shields.io/pypi/v/documenteer.svg?style=flat-square

.. image:: https://img.shields.io/pypi/l/documenteer.svg?style=flat-square

.. image:: https://img.shields.io/pypi/wheel/documenteer.svg?style=flat-square

.. image:: https://img.shields.io/pypi/pyversions/documenteer.svg?style=flat-square

Documentation tools for `LSST Data Management <http://dm.lsst.org>`_ projects, including Sphinx extensions.

Installation
============

::

   pip install documenteer

Development
===========

Create a virtual environment with your method of choice (virtualenvwrapper or conda) and then clone or fork, and install::

   git clone https://github.com/lsst-sqre/documenteer.git
   pip install -r requirements.txt

To make a release:

1. Update ``CHANGELOG.rst``.
2. Increment version in ``setup.py``.
3. Tag: ``git tag -s -m "vX.Y.Z" vX.Y.Z``
4. Push: ``git push --tags``

`Travis <https://travis-ci.org/lsst-sqre/documenteer>`_ should handle the PyPI deployment.

License and info
================

Copyright 2015-2017 Association of Universities for Research in Astronomy, Inc.

MIT licensed.
See `LICENSE <./LICENSE>`_ and `COPYRIGHT <./COPYRIGHT>`.
