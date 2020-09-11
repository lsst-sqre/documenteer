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
   * - :role:`ldm`
     - Link to an LDM document
   * - :role:`lse`
     - Link to an LSE document
   * - :role:`lpm`
     - Link to an LPM document
   * - :role:`lts`
     - Link to an LTS document
   * - :role:`lep`
     - Link to an LEP document
   * - :role:`lca`
     - Link to an LCA document
   * - :role:`lcr`
     - Link to an LCR document
   * - :role:`lso`
     - Link to an LSO document
   * - :role:`dmtr`
     - Link to a DMTR document
   * - :role:`sqr`
     - Link to a SQR document
   * - :role:`smtn`
     - Link to a SMTN document
   * - :role:`document`
     - Link to a DocuShare "Document" handle
   * - :role:`report`
     - Link to a DocuShare "Report" handle
   * - :role:`minutes`
     - Link to a DocuShare "Minutes" handle
   * - :role:`collection`
     - Link to a DocuShare "Collection" handle

Roles
=====

.. role:: ldm

   Link to an LDM document:

   .. code-block:: rst

      :ldm:`294`

   Output: :ldm:`294`

.. role:: lse

   Link to an LSE document:

   .. code-block:: rst

      :lse:`160`

   Output: :lse:`160`

.. role:: lpm

   Link to an LPM document:

   .. code-block:: rst

      :lpm:`51`

   Output: :lpm:`51`

.. role:: lts

   Link to an LTS document:

   .. code-block:: rst

      :lts:`488`

   Output: :lts:`488`

.. role:: lep

   Link to an LEP document:

   .. code-block:: rst

      :lep:`031`

   Output: :lep:`031`

.. role:: lca

   Link to an LCA document:

   .. code-block:: rst

      :lca:`227`

   Output: :lca:`227`

.. role:: lsstc

   Link to an LSSTC document.

.. role:: lcr

   Link to an LCR document.

.. role:: lcn

   Link to an LCN document.

.. role:: lso

   Link to an LSO document:

   .. code-block:: rst

      :lso:`011`

   Output: :lso:`011`

.. role:: dmtr

   Link to a DMTR document:

   .. code-block:: rst

      :dmtr:`141`

   Output: :dmtr:`141`

.. role:: sqr

   Link to a SQR document:

   .. code-block:: rst

      :sqr:`000`

   Output: :sqr:`000`

.. role:: dmtn

   Link to a DMTN document:

   .. code-block:: rst

      :dmtn:`000`

   Output: :dmtn:`000`

.. role:: smtn

   Link to a SMTN document:

   .. code-block:: rst

      :smtn:`001`

   Output: :smtn:`001`

.. role:: document

   Link to a DocuShare "Document" handle.

.. role:: report

   Link to a DocuShare "Report" handle.

.. role:: minutes

   Link to a DocuShare "Minutes" handle.

.. role:: collection

   Link to a DocuShare "Collection" handle.
