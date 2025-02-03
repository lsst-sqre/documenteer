####################
Start a new technote
####################

Rubin Observatory staff can start a new technote through their LSSTC Slack workspace account.
This page explains how to create a new technote project in either the Sphinx or ReStructuredText format.

Prerequisites
=============

To create and edit a technote, you'll need access to the `LSSTC Slack workspace`_.
You'll also need push access to the GitHub organization where your technote is hosted (different document series are hosted in different GitHub organizations, corresponding to the Rubin subsystem or team).
If you don't have push access in a whole organization, you can alternatively ask a leader in that organization to add you as a collaborator on the technote's repository once it's created.

Create a technote repository through Slack
==========================================

1. In Slack, open a |dmw-squarebot| and type:

.. code-block:: text

   create project

2. In response, a message with a drop-down appears. From the drop-down, select a template based on the preferred format:

   - For reStructuredText: :menuselection:`Documents --> Technote (reStructuredText)`
   - For Markdown: :menuselection:`Documents --> Technote (Markdown)`

3. Watch for threaded replies in Slack that provide a link to the GitHub repository and the technote's publication URL.

Next steps
==========

- :doc:`edit-locally`
- :doc:`edit-on-github`
