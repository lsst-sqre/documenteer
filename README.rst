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
   :alt: For Python 3.5+
   :target: https://pypi.python.org/pypi/documenteer

###########
Documenteer
###########

Sphinx documentation tools for `LSST Data Management <https://www.lsst.org/about/dm>`_ projects.

Browse the `lsst-doc-engineering <https://github.com/topics/lsst-doc-engineering>`_ GitHub topic for more LSST documentation engineering projects.

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
   pip install -e ".[dev]"

To make a release:

1. Update ``CHANGELOG.rst``.
2. Tag: ``git tag -s X.Y.Z -m "X.Y.Z"``
3. Push: ``git push --tags``

Use a `PEP 440-compliant <https://www.python.org/dev/peps/pep-0440/>`_ version identifiers.

`Travis CI <https://travis-ci.org/lsst-sqre/documenteer>`_ handles the PyPI deployment.

License and info
================

Documenteer is a project by the `Large Synoptic Survey Telescope <https://www.lsst.org>`_.

MIT licensed.
See `LICENSE <./LICENSE>`_ for details.
