################
Diagrams as code
################

Rubin user guides use Mermaid_ (through sphinxcontrib-mermaid_) for diagrams-as-code.
With Mermaid, you can express common diagram types like flow charts, sequence diagrams, and entity relationship diagrams with plain text source code.
The diagrams on rendered dynamically, within the web client.
Mermaid makes diagrams more maintainable since you don't need to manage proprietary graphics formats and binary files.

Basic syntax
============

Embedded diagrams
-----------------

Diagrams can be embedded directly in the page's source with the ``mermaid`` directive:

.. tab-set-code::

   .. code-block:: rst

     .. mermaid::

        flowchart LR
          rsp(Rubin Science Platform)
          rsp --> p(Portal)
          rsp --> n(Notebooks)
          rsp --> a(APIs)
          p --> a
          n --> a

   .. code-block:: md

     ```mermaid
     flowchart LR
       rsp(Rubin Science Platform)
       rsp --> p(Portal)
       rsp --> n(Notebooks)
       rsp --> a(APIs)
       p --> a
       n --> a
     ```

.. mermaid::

    flowchart LR
      rsp(Rubin Science Platform)
      rsp --> p(Portal)
      rsp --> n(Notebooks)
      rsp --> a(APIs)
      p --> a
      n --> a

Diagrams in separate files
--------------------------

You can create Mermaid_ diagrams in separate source files and reference them as arguments to the ``mermaid`` directive.

.. tab-set-code::

   .. code-block:: rst

      .. mermaid:: diagram.mmd

   .. code-block:: md

      ```mermaid diagram.mmd
      ```

This approach is great for complex diagrams, especially since some editors provide syntax highlighting and live preview for Mermaid_ diagrams.

Captions
--------

You can include a caption for the diagram with the ``caption`` option.

.. tab-set-code::

   .. code-block:: rst

      .. mermaid:: diagram.mmd
         :caption: My diagram.

   .. code-block:: md

      ```mermaid diagram.mmd
      :caption: My diagram.
      ```

Mermaid diagram types
=====================

Mermaid_ supports many diagram types, including:

- `Flowcharts <https://mermaid-js.github.io/mermaid/#/flowchart>`__
- `Sequence diagrams <https://mermaid-js.github.io/mermaid/#/sequenceDiagram>`__
- `Entity relationship diagrams <https://mermaid-js.github.io/mermaid/#/entityRelationshipDiagram>`__
- `Gantt <https://mermaid-js.github.io/mermaid/#/gantt>`__

See the Mermaid_ documentation for details on the available diagram types and their syntax.

Diagrams for architectural diagrams
===================================

Mermaid_ does not have support for architectural diagrams (that is, diagrams showing the infrastructure and services in a deployment).
For this application the Diagrams_ package, with the sphinx-diagrams_ extension, is ideal.

Installation and set up
-----------------------

sphinx-diagrams_ is not part of the standard Documenteer configuration for Rubin user guides.
You'll need to install and configure it:

1. Add the ``sphinx-diagrams`` Python dependency to your project's development/documentation requirements.

2. Ensure that ``graphviz`` is available in the build environment.
   If you are using GitHub Actions with an Ubuntu runner, this can be done with an apt installation:

   .. code-block:: yaml
      :caption: .github/workflows/ci.yaml

      - name: Install graphviz
        run: |
          sudo apt-get install -y graphviz

   If you are using tox_, you may need to add ``graphviz`` to the documentation environment's ``allowlist_externals`` configuration.

3. Add ``"sphinx_diagrams"`` to the extensions list in |documenteer.toml|:

   .. code-block:: toml
      :caption: documenteer.toml

      [sphinx]
      extensions = [
        "sphinx_diagrams"
      ]

Basic syntax
------------

You add Diagrams_\ -based diagrams to your documentation with ``diagrams`` directives.
As with Mermaid, you can write Diagrams_ code both within the ``diagrams`` directive, or set the name (or path) of a Python file as an argument to the ``diagrams`` diagram.
Referencing a Python module is recommended to take advantage of syntax highlighting in your code editor.

.. tab-set-code::

   .. code-block:: rst

      .. diagrams:: diagram.py

   .. code-block:: md

      ```diagrams diagram.py
      ```
