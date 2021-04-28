######################
Installing Documenteer
######################

.. _pip-install:

Installation with pip
=====================

You can install Documenteer from PyPI with pip:

.. code-block:: sh

   pip install documenteer

For different applications, install Documenteer with specific "extras" to bring in the necessary dependencies.

.. _install-technotes:

For technote projects:

.. code-block:: sh

   pip install "documenteer[technote]"

For LSST Stack projects (such as https://pipelines.lsst.io and EUPS packages):

.. code-block:: sh

   pip install "documenteer[pipelines]"

See :doc:`/pipelines/install` for more information.

Installation with Conda
=======================

Documenteer is available from `conda-forge`_ for Conda_ users.
First, enable the conda-forge channel:

.. code-block:: sh

   conda config --add channels conda-forge
   conda config --set channel_priority strict

To install only the core documenteer package:

.. code-block:: sh

   conda install documenteer

To install documenteer for technote projects:

.. code-block:: sh

   conda-install lsst-documenteer-technote

To install documenteer for LSST Stack projects (such as https://pipelines.lsst.io and EUPS packages):

.. code-block:: sh

   conda-install lsst-documenteer-pipelines

Installation from source
========================

See :doc:`/dev/development` for details.
