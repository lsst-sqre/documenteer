############################################
Installing Documenteer for pipelines.lsst.io
############################################

The "pipelines" version of Documenteer provides additional dependencies needed to build the `pipelines.lsst.io <https://pipelines.lsst.io>`_ documentation site for the LSST Science Pipelines.

Documenteer is already included in the Conda environment created by a typical LSST Science Pipelines installation, and no additional installation is needed.
This page provides additional installation instructions for atypical cases.

For both pip and conda, the installation needs to be done within the same Python/Conda environment that the Science Pipelines already installed in.
You can do that by running the Science Pipelines stack's :command:`setup` command _before_ installing Documenteer.

Pip installation of Documenteer
===============================

Install Documenteer with the ``pipelines`` extra:

.. code-block:: sh

   pip install documenteer[pipelines]

Besides ``documenteer``, you will also need to install graphviz to render API inheritance diagrams.

Conda installation
==================

First, enable the conda-forge channel:

.. code-block:: sh

   conda config --add channels conda-forge
   conda config --set channel_priority strict

Then install the `lsst-documenteer-pipelines <https://github.com/conda-forge/lsst-documenteer-feedstock>`_ metapackage.

.. code-block:: sh

   conda install lsst-documenteer-pipelines

Next steps
==========

- `Building single-package documentation locally <https://developer.lsst.io/stack/building-single-package-docs.html>`__ (DM Developer Guide)

- `Building the pipelines.lsst.io site locally <https://developer.lsst.io/stack/building-pipelines-lsst-io-locally.html>`__ (DM Developer Guide)
