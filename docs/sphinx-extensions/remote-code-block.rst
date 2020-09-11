.. default-domain:: rst

###############################
The remote code block extension
###############################

Documenteer provides a :dir:`remote-code-block` directive that works like :dir:`literalinclude`, but supports getting content from the web.

To use this directive, add the ``documenteer.sphinext.remotecodeblock`` extension to your :file:`conf.py` file:

.. code-block:: python

   extensions = ["documenteer.sphinxext.remotecodeblock"]

Directive
=========

.. directive:: .. remote-code-block:: url

   Include content from ``url`` in a literal code block.

   **Example**

   .. code-block:: rst

      .. remote-code-block:: https://raw.githubusercontent.com/lsst/templates/master/file_templates/stack_license_preamble_txt/template.txt.jinja
         :language: jinja

   Result:

   .. remote-code-block:: https://raw.githubusercontent.com/lsst/templates/master/file_templates/stack_license_preamble_txt/template.txt.jinja
      :language: jinja

   **Options**

   See the :dir:`literalinclude` documentation for available options.


Credit
======

:dir:`remote-code-block` is based on the implementation of Sphinx's :dir:`literalinclude`; copyright 2007-2018 by the Sphinx team.
