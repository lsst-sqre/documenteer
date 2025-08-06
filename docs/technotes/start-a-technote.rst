####################
Start a new technote
####################

Rubin Observatory staff can start a new technote through the rubin-obs.slack.com workspace.
This page explains how to create a new technote project in either the Markdown or reStructuredText format.

Prerequisites
=============

To create and edit a technote, you'll need access to the rubin-obs.slack.com workspace.
You'll also need push access to the technote.
If you don't have push access in the whole organization, you can ask an organization administrator to add you as a `collaborator <https://docs.github.com/en/organizations/managing-user-access-to-your-organizations-repositories/managing-outside-collaborators/adding-outside-collaborators-to-repositories-in-your-organization>`__ to the technote's repository after you create it.

 To create and edit a technote, you'll need:

  1. Access to the rubin-obs.slack.com workspace
  2. Push access to edit the technote repository after it's created

For GitHub access, you have two options:

- **Organization member**: If you have push access to the relevant GitHub organization (different technote series are hosted in different organizations), you'll automatically have access to your new technote repository.
- **External collaborator**: If you don't have organization-wide access, ask an organization administrator to add you as a `collaborator <https://docs.github.com/en/organizations/managing-user-access-to-your-organizations-repositories/managing-outside-collaborators/adding-outside-collaborators-to-repositories-in-your-organization>`__ to the technote repository once it's created.

Create a technote repository through Slack
==========================================

1. In the rubin-obs.slack.com workspace, send a message to ``@Squarebot``:

.. code-block:: text

   /msg @Squarebot create project

2. In response, a message with a drop-down appears. From the drop-down, select a template based on the preferred format:

   - For reStructuredText: :menuselection:`Documents --> Technote (reStructuredText)`
   - For Markdown: :menuselection:`Documents --> Technote (Markdown)`

3. Watch for threaded replies in Slack that provide a link to the GitHub repository and the technote's publication URL.

Next steps
==========

- :doc:`edit-locally`
- :doc:`edit-on-github`
