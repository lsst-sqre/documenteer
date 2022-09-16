######
Badges
######

Badges are colored pill-shapes containing text, like :bdg-info:`this`.
Used judiciously, they're effective for conveying information at a glance.
The Rubin user guide configuration enables your to use badges from the `Sphinx Design extension <https://sphinx-design.readthedocs.io/en/latest/badges_buttons.html#badges>`__.

Badge styles
============

.. list-table::
   :header-rows: 1

   * - Example
     - Syntax
   * - :bdg:`Plain badge`
     - ``:bdg:`Plain badge```
   * - :bdg-primary:`Primary`
     - ``:bdg-primary:`Primary```
   * - :bdg-primary-line:`Primary line`
     - ``:bdg-primary-line:`Primary line```
   * - :bdg-secondary:`Secondary`
     - ``:bdg-secondary:`Secondary```
   * - :bdg-secondary-line:`Secondary line`
     - ``:bdg-secondary-line:`Secondary line```
   * - :bdg-info:`Info`
     - ``:bdg-info:`Info```
   * - :bdg-info-line:`Info line`
     - ``:bdg-info-line:`Info line```
   * - :bdg-warning:`Warning`
     - ``:bdg-warning:`Warning```
   * - :bdg-warning-line:`Warning line`
     - ``:bdg-warning-line:`Warning line```
   * - :bdg-danger:`Danger`
     - ``:bdg-danger:`Danger```
   * - :bdg-danger-line:`Danger line`
     - ``:bdg-danger-line:`Danger line```
   * - :bdg-light:`Light`
     - ``:bdg-light:`Light```
   * - :bdg-light-line:`Light line`
     - ``:bdg-light-line:`Light line```
   * - :bdg-dark:`Dark`
     - ``:bdg-dark:`Dark```
   * - :bdg-dark-line:`Dark line`
     - ``:bdg-dark-line:`Dark line```

Reusable badges
===============

It's a good idea to use badges consistently throughout your documentation.
To do this, create substitutions for your badges in the :doc:`rst epilog <rst-epilog>`:

.. code-block:: rst
   :caption: _rst_epilog.rst

   .. |done| replace:: :bdg-success:`Done`
   .. |todo| replace:: :bdg-primary-line:`To-do`
   .. |inprogress| replace:: :bdg-seconday-line:`To-do`

Now you can use those badges throughout your documentation project:

.. code-block:: rst

   Project milestones
   ==================

   - |done| Task 1
   - |todo| Task 2
   - |inprogress| Task 2

See :doc:`rst-epilog` for configuration details.

Link and reference badges
=========================

Badges can also serve as links, both external and internal to the documentation project.

External links are ``bdg-link-*`` variants of the above link styles.
Explicit titles can be set using the normal ``<>`` syntax.

.. code-block:: rst

   :bdg-link-primary:`https://www.lsst.io`

   :bdg-link-primary:`Rubin Documentation <https://www.lsst.io>`

You can reference targets (:external+sphinx:rst:role:`ref`) in a badge using ``bdg-ref-*`` variants of badges:

.. code-block:: rst

   :bdg-ref-primary:`a-target`

   :bdg-ref-primary:`Title <a-target>`
