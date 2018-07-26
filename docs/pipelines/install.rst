############################################
Installing Documenteer for pipelines.lsst.io
############################################

Installation in the Stack environment
=====================================

The "pipelines" version of Documenteer provides additional dependencies needed to build the `pipelines.lsst.io <https://pipelines.lsst.io>`_ documentation site for the LSST Science Pipelines.
Since Documenteer needs to work inside the Python environment of LSST DM's EUPS Stack, the safest way to install Documenteer is in a virtual environment layered on top of the Stack's Python.

First, `install and set up <https://pipelines.lsst.io/install/newinstall.html>`__ the LSST Science Pipeline Stack.

Then create a virtual environment and install the "pipelines" version of Documenteer into it:

.. code-block:: bash

   python -m venv --system-site-packages --without-pip pyvenv
   source pyvenv/bin/activate
   curl https://bootstrap.pypa.io/get-pip.py | python
   pyvenv/bin/pip install "documenteer[pipelines]"

Documenteer requires Python 3.5 and newer.

.. tip::

   When working with the LSST Science Pipelines, the best method for installing Documenteer is through the `requirements.txt <https://github.com/lsst/pipelines_lsst_io/blob/master/requirements.txt>`__ file in the `pipelines_lsst_io <https://github.com/lsst/pipelines_lsst_io>`_ repository.
   This way your working copy of Documenteer is compatible with the documentation project.

Further reading
===============

.. FIXME update these links to developer.lsst.io

- `Building single-package documentation locally <https://developer.lsst.io/v/DM-14852/stack/building-single-package-docs.html>`__ (DM Developer Guide)

- `Building the pipelines.lsst.io site locally <https://developer.lsst.io/v/DM-14852/stack/building-pipelines-lsst-io-locally.html>`__ (DM Developer Guide)
