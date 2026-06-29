#######################
Diagrams extension test
#######################

Inline diagram:

.. diagrams::

   from diagrams.k8s.compute import Pod
   from documenteer.ext.diagrams import SphinxDiagram

   with SphinxDiagram(title="Inline"):
       Pod("inline-pod")

External diagram from a file:

.. diagrams:: diagram.py
