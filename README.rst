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

To make a release:

1. Update the :file:`CHANGELOG.rst`.
2. Increment version in :file:`setup.py`.
3. Tag: ``git tag -s -m "Version X.Y.Z" vX.Y.Z``
4. Build:

   .. code-block:: bash

      rm -R dist
      python setup.py sdist bdist_wheel

5. Upload:

   .. code-block:: bash

      twine upload dist/*
      git push --tags

License
=======

MIT Licensed. See :file:`LICENSE` and :file:`COPYRIGHT`.
