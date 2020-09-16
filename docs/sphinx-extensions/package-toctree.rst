.. default-domain:: rst

######################################################
Package toctree extension for LSST Stack documentation
######################################################

Documenteer provides the :dir:`package-toctree` :dir:`module-toctree` directives that are useful building dynamic toctrees of package and module documentation in stack documentation projects like the LSST Science Pipelines (https://pipelines.lsst.io).

To use this Sphinx extension, add ``documenteer.sphinxext.packagetoctree`` to your :file:`conf.py` file:

.. code-block:: python

   extensions = ["documenteer.sphinxext.packagetoctree"]

To learn more about the build process for stack documentation projects, see :doc:`/pipelines/build-overview`.

Summary
=======

.. list-table:: Directives
   :widths: 33 66
   :header-rows: 1

   * - Directive
     - Purpose
   * - :dir:`package-toctree`
     - Create a toctree of package homepages.
   * - :dir:`module-toctree`
     - Create a toctree of module homepages.

Directives
==========

.. directive:: .. package-toctree::

   The ``package-toctree`` directive creates a :dir:`toctree` of package documentation homepages found in a stack documentation project.
   Stack packages have index pages with paths ``/packages/{{name}}/index.rst`` within project.
   For more information about package documentation homepages, see the `Layout of the doc/ directory <https://developer.lsst.io/stack/layout-of-doc-directory.html>`_ and `Package homepage topic type <https://developer.lsst.io/stack/package-homepage-topic-type.html>`_ pages in the LSST DM Developer Guide.

   Basic example:

   .. code-block:: rst

      .. package-toctree::

   **Options**

   skip: package-list
      To exclude specific EUPS packages from the toctree, provide a comma-separated list of EUPS package names:

      .. code-block:: rst

         .. package-toctree::
            :skip: afw, utils

.. directive:: .. module-toctree::

   The ``module-toctree`` directive creates a :dir:`toctree` of module documentation homepages found in a stack documentation project.
   Modules have index pages with paths ``/module/{{name}}/index.rst`` within a Stack documentation project.
   For more information about module documentation homepages, see the `Layout of the doc/ directory <https://developer.lsst.io/stack/layout-of-doc-directory.html>`_ and `Module homepage topic type <https://developer.lsst.io/stack/module-homepage-topic-type.html>`_ pages in the LSST DM Developer Guide.

   Basic example:

   .. code-block:: rst

      .. module-toctree::

   **Options**

   skip: module-list
      To exclude specific modules from the toctree, provide a comma-separated list of module names:

      .. code-block:: rst

         .. module-toctree::
            :skip: lsst.afw.image, lsst.afw.fits
