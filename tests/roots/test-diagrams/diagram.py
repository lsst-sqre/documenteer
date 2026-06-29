from diagrams.k8s.compute import Pod

from documenteer.ext.diagrams import SphinxDiagram

with SphinxDiagram(title="External"):
    Pod("external-pod")
