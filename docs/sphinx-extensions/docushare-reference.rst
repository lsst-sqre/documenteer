.. default-domain:: rst

#############################
LSST document reference roles
#############################

Documenteer provides reStructuredText roles that simplify linking to LSST documents according to their handle.

To use these roles, add the ``documenteer.sphinext.lsstdocushare`` extension to your :file:`conf.py` file:

.. code-block:: python

   extensions = ["documenteer.sphinxext.lsstdocushare"]

Summary
=======

.. list-table:: Document link roles
   :widths: 25 75
   :header-rows: 1

   * - Role
     - Purpose

   * - :role:`collection`
     - Link to a DocuShare "Collection" handle
   * - :role:`ittn`
     - Link to an ITTN technical note
   * - :role:`dmtn`
     - Link to a DMTN technical note
   * - :role:`dmtr`
     - Link to a DMTR document
   * - :role:`document`
     - Link to a DocuShare "Document" handle
   * - :role:`lca`
     - Link to an LCA document
   * - :role:`lcn`
     - Link to an LCN document
   * - :role:`lcr`
     - Link to an LCR document
   * - :role:`ldm`
     - Link to an LDM document
   * - :role:`lep`
     - Link to an LEP document
   * - :role:`lpm`
     - Link to an LPM document
   * - :role:`lse`
     - Link to an LSE document
   * - :role:`lsstc`
     - Link to an LSSTC document
   * - :role:`lso`
     - Link to an LSO document
   * - :role:`lts`
     - Link to an LTS document
   * - :role:`minutes`
     - Link to a DocuShare "Minutes" handle
   * - :role:`pstn`
     - Link to a PSTN technical note
   * - :role:`rtn`
     - Link to an RTN technical note
   * - :role:`sitcomtn`
     - Link to a SITCOMTN technical note
   * - :role:`smtn`
     - Link to a SMTN technical note
   * - :role:`sqr`
     - Link to a SQR technical note
   * - :role:`tstn`
     - Link to a Telescope & Site technical note
   * - :role:`report`
     - Link to a DocuShare "Report" handle

Roles
=====

Links DocuShare
---------------

.. role:: collection

   Link to a DocuShare "Collection" handle.

.. role:: dmtr

   Link to a DMTR document:

   .. code-block:: rst

      :dmtr:`141`

   Output: :dmtr:`141`

.. role:: document

   Link to a DocuShare "Document" handle.

.. role:: lca

   Link to an LCA document:

   .. code-block:: rst

      :lca:`227`

   Output: :lca:`227`

.. role:: lcn

   Link to an LCN document.

.. role:: lcr

   Link to an LCR document.

.. role:: ldm

   Link to an LDM document:

   .. code-block:: rst

      :ldm:`294`

   Output: :ldm:`294`

.. role:: lep

   Link to an LEP document:

   .. code-block:: rst

      :lep:`031`

   Output: :lep:`031`

.. role:: lpm

   Link to an LPM document:

   .. code-block:: rst

      :lpm:`51`

   Output: :lpm:`51`

.. role:: lse

   Link to an LSE document:

   .. code-block:: rst

      :lse:`160`

   Output: :lse:`160`

.. role:: lsstc

   Link to an LSSTC document.

.. role:: lso

   Link to an LSO document:

   .. code-block:: rst

      :lso:`011`

   Output: :lso:`011`

.. role:: lts

   Link to an LTS document:

   .. code-block:: rst

      :lts:`488`

   Output: :lts:`488`

.. role:: minutes

   Link to a DocuShare "Minutes" handle.

.. role:: report

   Link to a DocuShare "Report" handle.

Links to technical notes on lsst.io
-----------------------------------

.. role:: dmtn

   Link to a DMTN document:

   .. code-block:: rst

      :dmtn:`000`

   Output: :dmtn:`000`

.. role:: ittn

   Link to an ITTN document:

   .. code-block:: rst

      :ittn:`001`

   Output: :ittn:`001`

.. role:: pstn

   Link to a PSTN document:

   .. code-block:: rst

      :pstn:`001`

   Output: :pstn:`001`

.. role:: rtn

   Link to an RTN document:

   .. code-block:: rst

      :rtn:`001`

   Output: :rtn:`001`

.. role:: sitcomtn

   Link to a SITCOMTN document:

   .. code-block:: rst

      :sitcomtn:`001`

   Output: :sitcomtn:`001`

.. role:: smtn

   Link to a SMTN document:

   .. code-block:: rst

      :smtn:`001`

   Output: :smtn:`001`

.. role:: sqr

   Link to a SQR document:

   .. code-block:: rst

      :sqr:`000`

   Output: :sqr:`000`

.. role:: tstn

   Link to a TSTN document:

   .. code-block:: rst

      :tstn:`001`

   Output: :tstn:`001`
