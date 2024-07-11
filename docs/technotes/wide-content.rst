############################################################
Accommodating wide content (tables, code blocks, and images)
############################################################

Technotes use a narrow content column to improve readability.
However, some content types need to more horizontal space.
This page explains how to use the ``technote-wide-content`` CSS utility class to let content span the full width of the page.

Tables and code blocks
======================

To allow a table or code block to span the available horizontal space on a page, you can preceed it with the ``technote-wide-content`` class in a ``rst-class`` directive.
The ``rst-class`` directive is not part of the table or code-block's directive, but is a separate preceeding directive that applies the ``technote-wide-content`` class to the following content.

Tables
------

.. tab-set::

   .. tab-item:: reStructuredText
      :sync: rst

      .. code-block:: rst

         .. rst-class:: technote-wide-content

         +-----------------+-----------------+
         | Header 1        | Header 2        |
         +=================+=================+
         | Row 1, Column 1 | Row 1, Column 2 |
         +-----------------+-----------------+
         | Row 2, Column 1 | Row 2, Column 2 |
         +-----------------+-----------------+

   .. tab-item:: markdown
        :sync: md

        .. code-block:: md

           ```{rst-class} technote-wide-content
           ```

           | Header 1        | Header 2        |
           | --------------- | --------------- |
           | Row 1, Column 1 | Row 1, Column 2 |
           | Row 2, Column 1 | Row 2, Column 2 |

List tables
-----------

.. tab-set::

   .. tab-item:: reStructuredText
      :sync: rst

      .. code-block:: rst

         .. rst-class:: technote-wide-content

         .. list-table::
            :header-rows: 1

            * - Header 1
              - Header 2
            * - Row 1, Column 1
              - Row 1, Column 2
            * - Row 2, Column 1
              - Row 2, Column 2

   .. tab-item:: markdown

      .. code-block:: md

         ```{rst-class} technote-wide-content
         ```

         ```{list-table}
         :header-rows: 1

         * - Header 1
           - Header 2
         * - Row 1, Column 1
           - Row 1, Column 2
         * - Row 2, Column 1
           - Row 2, Column 2
         ```

Code blocks
-----------

.. tab-set::

   .. tab-item:: reStructuredText
      :sync: rst

      .. code-block:: rst

         .. rst-class:: technote-wide-content

         .. code-block:: python

            def my_function():
                return "Hello, world!"

   .. tab-item:: markdown
      :sync: md

      .. code-block:: md

         ```{rst-class} technote-wide-content
         ```

         ```python
         def my_function():
             return "Hello, world!"
         ```

Images and figures
==================

In technotes, plots and images should be presented with the ``figure`` directive so that they can be captioned and referenced.
Figures support a ``figclass`` option that is compatible with the ``technote-wide-content`` class, which lets you avoid using a separate ``rst-class`` directive.

.. tab-set::

   .. tab-item:: reStructuredText
      :sync: rst

      .. code-block:: rst

         .. figure:: my-plot.png
            :figclass: technote-wide-content

            My plot.

   .. tab-item:: markdown
      :sync: md

      .. code-block:: md

         ```{figure} my-plot.png
         :figclass: technote-wide-content

         My plot.
         ```
