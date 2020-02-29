######################
Installing Documenteer
######################

.. _pip-install:

Installation with pip
=====================

You can install Documenteer from PyPI with pip.
For different applications, install Documenteer with specific "extras" to bring in the necessary dependencies.

.. _install-technotes:

For technote projects:

.. code-block:: sh

   pip install "documenteer[technote]"

For LSST Stack projects (such as https://pipelines.lsst.io and EUPS packages):

.. code-block:: sh

   pip install "documenteer[pipelines]"

See :doc:`/pipelines/install` for more information.

Installation from source
========================

See :doc:`/dev/development` for details.
