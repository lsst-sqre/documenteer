.. default-domain:: rst

####################
Jira reference roles
####################

Documenteer provides reStructuredText roles to simplify linking to issues in LSST's Jira ticketing system at https://jira.lsstcorp.org.

To use these roles, add the ``documenteer.sphinxext.jira`` extension to your :file:`conf.py` file:

.. code-block:: python

   extensions = ["documenteer.sphinxext.jira"]

Roles
=====

.. role:: jira

   Link to a Jira issue using the issue ID as an argument.
   Example:

   .. code-block:: rst

      :jira:`DM-22957`

   Output: :jira:`DM-22957`

.. role:: jirap

   Link to a Jira issue using the issue ID as an argument, with the link enclosed in parentheses.
   Example:

   .. code-block:: rst

      :jirap:`DM-22957`

   Output: :jirap:`DM-22957`

.. role:: jirab

   Link to a Jira issue using the issue ID as an argument, with the link enclosed in square brackets.
   Example:

   .. code-block:: rst

      :jirab:`DM-22957`

   Output: :jirab:`DM-22957`
