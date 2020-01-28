############################################
Installing Documenteer for pipelines.lsst.io
############################################

The "pipelines" version of Documenteer provides additional dependencies needed to build the `pipelines.lsst.io <https://pipelines.lsst.io>`_ documentation site for the LSST Science Pipelines.

At the moment, the recommended procedure for installing Documenteer for stack work is to pip-install it into the set up Conda environment, using the version corresponding to the ``master`` branch of the pipelines_lsst_io_ repository.

.. _pipelines_lsst_io: https://github.com/lsst/pipelines_lsst_io

Prerequisites
=============

Before starting this tutorial, you’ll need a working stack.
For more information, see the `LSST Science Pipelines installation guide`_.

The stack environment must be set up in the shell that you are installing Documenteer with.

.. _`LSST Science Pipelines installation guide`: https://pipelines.lsst.io/install/newinstall.html

Pip installation of Documenteer
===============================

Install Documenteer based on the requirements of the pipelines_lsst_io_ repository:

.. code-block:: sh

   curl -O https://raw.githubusercontent.com/lsst/pipelines_lsst_io/master/requirements.txt
   pip install -r requirements.txt

.. tip::

   Do this step *after* having set up the stack with the :command:`setup` command.

Next steps
==========

- `Building single-package documentation locally <https://developer.lsst.io/stack/building-single-package-docs.html>`__ (DM Developer Guide)

- `Building the pipelines.lsst.io site locally <https://developer.lsst.io/stack/building-pipelines-lsst-io-locally.html>`__ (DM Developer Guide)
