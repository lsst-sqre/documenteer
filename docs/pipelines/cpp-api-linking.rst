.. default-domain:: rst

######################################################################
Cross-linking the Doxygen-built C++ API reference with the lsstcc role
######################################################################

The pipelines.lsst.io_ project includes an embedded Doxygen_ \-generated subsite to document the LSST Science Pipelines's C++ API.
For more information about the Doxygen subsite, see :ref:`pipelines-build-doxygen` from the pipelines.lsst.io build overview.

This page describes how to link between reStructuredText content and the C++ API reference.

.. _lsstcc:

Link to C++ APIs with the lsstcc role
=====================================

The Sphinx configuration for the pipelines.lsst.io project includes a special :role:`lsstcc` role that replaces the use of Sphinx's native domain cross links (the single backtick syntax).

.. warning::

   Some of LSST's C++ APIs are not compatible with doxylink_.
   In particular, method that use the ``noexcept`` operator, are ``operator()``, or use macros like ``PTR``, don't seem to be linkable with doxylink_ 1.6.

   Use the :ref:`stack-docs listcc command <lsstcc-listcc>` to identify linkable API signatures.
   As a last resort, you may want to manually create a relative hyperlink.
   Contact `#dm-docs`_ on Slack for help.

.. role:: lsstcc

   Use the ``lsstcc`` role to link to a C++ API in the Doxygen subsite.

   Link to a class:

   .. code-block:: rst

      :lsstcc:`lsst::afw::table::Schema`

   Link to a method:

   .. code-block:: rst

      :lsstcc:`lsst::afw::table::Schema::getRecordSize`

   Overloaded functions must be linked with their full signature.
   In that case, escape any angle brackes with a backslash (``<`` → ``\<`` and ``>`` → ``\>``):

   .. code-block:: rst

      :lsstcc:`lsst::afw::table::KeyBase\< Flag \>`

   .. tip::

      By default, the :ref:`stack-docs listcc <lsstcc-listcc>` command shows escaped API signatures, ready to copy and paste into an ``lsstcc`` role.

   You can customized the displayed test of the API link by enclosing the displayed test in angle brackets (that's why you need to escape angle brackets in signatures):

   .. code-block:: rst

      :lsstcc:`lsst::afw::table::Schema <Schema>`

    In the above example, the linked text will be "Schema."
    The ``~`` prefix, used in Python domain links, does not work with the ``lsstcc`` role; using angle brackets to explicitly rename a link lets you achieve the same result.

.. _lsstcc-listcc:

Listing linkable C++ APIs (stack-docs listcc)
=============================================

Documenteer includes the :doc:`stack-docs listcc <stack-docs-cli>` command that helps you find C++ APIs that are linkable with the :role:`lsstcc` role.
The APIs are automatically escaped so that you can copy-and-paste them into the :role:`lsstcc` role in a reStructuredText document.

From the pipelines_lsst_io_ project repository, run the command to see the signatures of all available APIs:

.. prompt:: bash

   stack-docs listcc

You filter the signatures with a regular expression pattern.
To filter only the ``lsst::afw::table`` APIs:

.. prompt:: bash

   stack-docs listcc -p lsst::afw::table

The ``-p`` optional accepts any Python regular expression syntax.

Additionally, you can also filter by type.
For example, to see only header files:

.. prompt:: bash

   stack-docs listcc -t file

You can supply multiple ``-t`` options.
To see both classes and functions:

.. prompt:: bash

   stack-docs listcc -t class -t function

The available types are:

- class
- define
- enumeration
- file
- function
- group
- namespace
- struct
- typedef
- variable

.. seealso::

   For more information, see the reference documentation for the :doc:`stack-docs command <stack-docs-cli>`.
