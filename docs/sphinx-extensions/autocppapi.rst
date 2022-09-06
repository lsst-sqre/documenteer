.. default-domain:: rst

#######################################################################
The autocppapi extension for listing Doxylink C++ APIs through Doxylink
#######################################################################

Documenteer provides an :dir:`autocppapi` directive that serves a similar role as automodapi_, but instead provides a listing of APIs in a C++ namespace.
The :dir:`autocppapi` works with Doxylink_ to link to APIs in a Doxygen site.

To use this directive, add the ``documenteer.ext.autocppapi`` extension to your :file:`conf.py` file:

.. code-block:: python

   extensions = [..., "sphinxcontrib.doxylink", "documenteer.ext.autocppapi"]

.. important::

   The ``autocppapi`` extension needs Doxylink to be installed and also included in the extensions listing.
   If you installed ``autocppapi`` through the :ref:`"pipelines" extra <pip-install>`, Doxylink will be installed for you.
   Doxylink is automatically configured in Pipelines documentation builds to point to a Doxygen site that's embedded during the build process (see :doc:`/pipelines/build-overview`).
   Otherwise, you can manually add Doxylink to your project's depenencies:

   .. prompt:: bash

      pip install sphinxcontrib-doxylink

autocppapi directive
====================

.. directive:: .. autocppapi:: namespace

   Create a listing of APIs associated with the given namespace.
   The listing is broken into subsections for each type of API:

   - Classes
   - Structs
   - Variables
   - Defines

   Each listed item is a link into the Doxygen C++ API reference.

   **Example**

   .. code-block:: rst

      .. autocppapi:: lsst::afw::image

   This example produces a listing of APIs associated with the ``lsst::afw::image`` namespace.
   In order to use ``autocppapi`` like this, without additional options, you need to set the ``documenteer_autocppapi_doxylink_role`` configuration value in your :file:`conf.py` file.

   **Options**

   ``:doxylink-role:`` role-name
      Set this option to the name of the Doxylink role instead of using the ``documenteer_autocppapi_doxylink_role`` configuration variable.

Configurations
==============

``documenteer_autocppapi_doxylink_role``
    Set this configuration variable to the name of the Doxylink role.
    As an example, this is how pipelines.lsst.io configures the extension:

    .. code-block:: python

       doxylink = {"lsstcc": ("_doxygen/doxygen.tag", "cpp-api")}

       documenteer_autocppapi_doxylink_role = "lsstcc"

    To override this configuration on a per-\ ``autocppapi`` directive basis, you can use the directive's ``:doxylink-role:`` option instead.
