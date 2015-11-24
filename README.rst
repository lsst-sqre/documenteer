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

.. code-block:: bash

   pip install documenteer

Development
===========

Create a virtual environment with your method of choice (virtualenvwrapper or conda) and then clone or fork, and install::

.. code-block:: bash

   git clone https://github.com/lsst-sqre/documenteer.git
   pip install -r requirements.txt
   python setup.py develop

We use `zest.releaser <http://zestreleaser.readthedocs.org>`_ to manage releases.
To make a release

1. Update the :file:`CHANGELOG.rst`
2. Run ``fullrelease``
3. ``git push --tags``

License
=======

MIT Licensed. See :file:`LICENSE` and :file:`COPYRIGHT`.
