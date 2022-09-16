########
Tab sets
########

Tab sets enable you to to render parallel documentation fragments where only one pane is visible at a time.
Tab sets are useful for multi-lingual code samples — like how this documentation shows how to write documentation in either reStructuredText or Markdown.

Tab sets on a page can be synchronized.
For example, if a user selects reStructuredText for one tab set, all other tab sets automatically switch to that same preference.

Tab sets are provided through the `Sphinx Design`_ extension.

Create a tab set
================

.. tab-set::

   .. tab-item:: reStructuredText
      :sync: rst

      .. code-block:: rst

         .. tab-set::

            .. tab-item:: reStructuredText

               .. code-block:: rst

                  `Rubin Observatory <https://www.lsst.org>`__

            .. tab-item:: markdown

               .. code-block:: md

                  [Rubin Observatory](https://www.lsst.org)

   .. tab-item:: markdown
      :sync: md

       .. code-block:: markdown

          ::::{tab-set}

          :::{tab-item} reStructuredText
          ```rst
          `Rubin Observatory <https://www.lsst.org>`__
          ```
          :::

          :::{tab-item} markdown
          ```md
          [Rubin Observatory](https://www.lsst.org)
          ```
          :::

          ::::

Synchronized tab sets
=====================

To synchronize multiple tab sets, add a ``sync`` option to each ``tab-item`` with consistent keys.

.. tab-set::

   .. tab-item:: reStructuredText
      :sync: rst

      .. code-block:: rst

         .. tab-set::

            .. tab-item:: reStructuredText
               :sync: rst

               .. code-block:: rst

                  `Rubin Observatory <https://www.lsst.org>`__

            .. tab-item:: markdown
               :sync: md

               .. code-block:: md

                  [Rubin Observatory](https://www.lsst.org)

   .. tab-item:: markdown
      :sync: md

       .. code-block:: markdown

          ::::{tab-set}

          :::{tab-item} reStructuredText
          :sync: rst
          ```rst
          `Rubin Observatory <https://www.lsst.org>`__
          ```
          :::

          :::{tab-item} markdown
          :sync: md
          ```md
          [Rubin Observatory](https://www.lsst.org)
          ```
          :::

          ::::

Automatic tab items for code samples
====================================

If the tab items contain only code, you can use the ``tab-set-code`` directive instead of ``tab-set``.
In that case, each ``code-block``, ``code`` or ``literalinclude`` in the ``tab-set-code`` is treated as a tab item, that's automatically labeled and synchronized by language.

.. tab-set-code::

   .. code-block:: rst

       .. tab-set-code::

          .. code-block:: rst

             `Rubin Observatory <https://www.lsst.org>`__

          .. code-block:: md

             [Rubin Observatory](https://www.lsst.org)

   .. code-block:: markdown

      ::::{tab-set-code}

      ```rst
      `Rubin Observatory <https://www.lsst.org>`__
      ```

      ```md
      [Rubin Observatory](https://www.lsst.org)
      ```

      ::::
