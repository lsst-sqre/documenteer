###############################################################
Sphinx extensions for the LSST Science Pipelines task framework
###############################################################

These extensions allow you to document and reference tasks in the LSST Science Pipelines.

Enable these extensions by adding ``documenteer.sphinxext.lssttasks`` to the Sphinx project's ``extensions`` configuration list.

To use this Sphinx extension, add ``documenteer.sphinxext.lssttasks`` to your :file:`conf.py` file:

.. code-block:: python

   extensions = ["documenteer.sphinxext.lssttasks"]

The ``documenteer.conf.pipelines`` and ``documenteer.conf.pipelinespkg`` configurations automatically add these extensions to LSST Science Pipelines package documentation projects.

Listing configuration fields
============================

These directives list configuration fields associated with a task or configuration class:

- :rst:dir:`lsst-task-config-fields`
- :rst:dir:`lsst-task-config-subtasks`
- :rst:dir:`lsst-config-fields`

.. rst:directive:: .. lsst-task-config-fields:: task_name

   List the configuration fields (except for ``ConfigurableField`` and ``Registry``) for a task class.

   Use this directive in the "Configuration fields" component of Task documentation topics.

   **Required argument:**

   - Name of the task class.

   **Example:**

   .. code-block:: rst

      .. lsst-task-config-fields:: lsst.pipe.tasks.processCcd.ProcessCcdTask

   **See also:**

   - :rst:dir:`lsst-task-config-subtasks`: lists subtasks instead of general configuration fields.
   - :rst:role:`lsst-config-field`: role for cross-referencing individual fields documented with this directive.

.. rst:directive:: .. lsst-task-config-subtasks:: task_name

   List the subtask configuration fields (``ConfigurableField`` and ``Registry`` types) for a task class.

   Use this directive in the "Configurable subtasks" component of Task documentation topics.

   **Required argument:**

   - Name of the task class.

   **Example:**

   .. code-block:: rst

      .. lsst-task-config-subtasks:: lsst.pipe.tasks.processCcd.ProcessCcdTask

   **See also:**

   - :rst:dir:`lsst-task-config-fields`: lists general configuration fields (not of the ``ConfigurableField`` and ``Registry`` types).
   - :rst:role:`lsst-config-field`: role for cross-referencing individual fields documented with this directive.

.. rst:directive:: .. lsst-config-fields:: config_name

   List all configuration fields associated with a configuration class (subclass of ``lsst.pex.config.Config``).

   Use this directive in standalone configuration topics.

   **Required argument:**

   - Name of the config class.

   **Example:**

   .. code-block:: rst

      .. lsst-config-fields:: lsst.pipe.tasks.colorterms.Colorterm

   **See also:**

   - Use :rst:dir:`lsst-task-config-fields` or :rst:dir:`lsst-task-config-subtasks` to list configuration fields when working within a task topic.
   - :rst:role:`lsst-config-field`: role for cross-referencing individual fields documented with this directive.

.. _lssttasks-topic-markers:

Topic markers
=============

These directives mark task and configuration topic types:

- :rst:dir:`lsst-task-topic`
- :rst:dir:`lsst-config-topic`

Use these directives at the top of either a task or standalone config topic page.

.. rst:directive:: .. lsst-task-topic:: task_name

   Mark the page as a task topic.

   **Required argument:**

   - Name of the task class.

   **Content:**

   You can optionally add a one or two sentence summary of the task as the directive's content.
   This summary is used by the :ref:`topic listing directives <lssttasks-topic-listings>`.
   This content is **optional**.
   If not set, the summary is set from the task's docstring.

   **Example:**

   .. code-block:: rst

      .. lsst-task-topic:: lsst.pipe.tasks.processCcd.ProcessCcdTask

         Summary of ProcessCcdTask.

.. rst:directive:: .. lsst-config-topic:: config_name

   Mark the page as a standalone configuration topic.

   **Required argument:**

   - Name of the config class.

   **Content:**

   You can optionally add a one or two sentence summary of the config as the directive's content.
   This summary is used by the :ref:`topic listing directives <lssttasks-topic-listings>`.
   This content is **optional**.
   If not set, the summary is set from the config's docstring.

   **Example:**

   .. code-block:: rst

      .. lsst-config-topic:: lsst.pipe.tasks.colorterms.Colorterm

         Summary of Colorterm.

.. _lssttasks-topic-listings:

Topic listings
==============

These directives make listings of topics labeled by :ref:`topic markers <lssttasks-topic-markers>`:

- :rst:dir:`lsst-tasks`
- :rst:dir:`lsst-cmdlinetasks`
- :rst:dir:`lsst-pipelinetasks`
- :rst:dir:`lsst-configurables`
- :rst:dir:`lsst-configs`

.. rst:directive:: lsst-tasks

   List task topics that are marked with the :rst:dir:`lsst-task-topic` directive.
   Only ``lsst.pipe.base.Task``-types that are not ``CmdLineTask`` or ``PipelineTask``-types are listed by this directive.

   **Options**

   ``root``
      The root Python package that tasks must belong to to be including in the listing.
      For example, ``:root: lsst.pipe.tasks`` means that only tasks in the ``lsst.pipe.tasks`` Python subpackage are included in the listing.

   ``toctree``
      If set, a :rst:dir:`toctree` is automatically generated for pages that appear in a given directory.
      For example, if task topics are in a ``tasks/`` subdirectory, set ``:toctree: tasks``.
      The :rst:dir:`toctree` is hidden.

      If this directive is listing topics that are already included by another :rst:dir:`toctree`, **don't set this option.**

      Note that ``toctree`` doesn't filter tasks using the same critera as the ``root`` option.
      Generally the directory structure should be set up so that ``toctree`` effectively corresponds to the filtering criteria set by ``root``, though.

   **Example:**

   .. code-block:: rst

      .. lsst-tasks::
         :root: lsst.pipe.tasks
         :toctree: tasks

.. rst:directive:: lsst-cmdlinetasks

   List task topics that are marked with the :rst:dir:`lsst-task-topic` directive that correspond to ``lsst.pipe.base.CmdLineTask``-types.

   **Options**

   ``root``
      The root Python package that tasks must belong to to be including in the listing.
      For example, ``:root: lsst.pipe.tasks`` means that only tasks in the ``lsst.pipe.tasks`` Python subpackage are included in the listing.

   ``toctree``
      If set, a :rst:dir:`toctree` is automatically generated for pages that appear in a given directory.
      For example, if task topics are in a ``tasks/`` subdirectory, set ``:toctree: tasks``.
      The :rst:dir:`toctree` is hidden.

      If this directive is listing topics that are already included by another :rst:dir:`toctree`, **don't set this option.**

      Note that ``toctree`` doesn't filter tasks using the same critera as the ``root`` option.
      Generally the directory structure should be set up so that ``toctree`` effectively corresponds to the filtering criteria set by ``root``, though.

   **Example:**

   .. code-block:: rst

      .. lsst-cmdlinetasks::
         :root: lsst.pipe.tasks
         :toctree: tasks

.. rst:directive:: lsst-pipelinetasks

   List task topics that are marked with the :rst:dir:`lsst-task-topic` directive that correspond to ``lsst.pipe.base.PipelineTask``-types.

   **Options**

   ``root``
      The root Python package that tasks must belong to to be including in the listing.
      For example, ``:root: lsst.pipe.tasks`` means that only tasks in the ``lsst.pipe.tasks`` Python subpackage are included in the listing.

   ``toctree``
      If set, a :rst:dir:`toctree` is automatically generated for pages that appear in a given directory.
      For example, if task topics are in a ``tasks/`` subdirectory, set ``:toctree: tasks``.
      The :rst:dir:`toctree` is hidden.

      If this directive is listing topics that are already included by another :rst:dir:`toctree`, **don't set this option.**

      Note that ``toctree`` doesn't filter tasks using the same critera as the ``root`` option.
      Generally the directory structure should be set up so that ``toctree`` effectively corresponds to the filtering criteria set by ``root``, though.

   **Example:**

   .. code-block:: rst

      .. lsst-pipelinetasks::
         :root: lsst.pipe.tasks
         :toctree: tasks

.. rst:directive:: lsst-configurables

   List "configurable" topics that are marked with the :rst:dir:`lsst-task-topic` directive that correspond to generic configurable types.

   **Options**

   ``root``
      The root Python package that configurables must belong to to be including in the listing.
      For example, ``:root: lsst.pipe.tasks`` means that only configurables in the ``lsst.pipe.tasks`` Python subpackage are included in the listing.

   ``toctree``
      If set, a :rst:dir:`toctree` is automatically generated for pages that appear in a given directory.
      For example, if configurable topics are in a ``configurables/`` subdirectory, set ``:toctree: configurables``.
      The :rst:dir:`toctree` is hidden.

      If this directive is listing topics that are already included by another :rst:dir:`toctree`, **don't set this option.**

   **Example:**

   .. code-block:: rst

      .. lsst-configurables::
         :root: lsst.pipe.tasks
         :toctree: configurables

.. rst:directive:: lsst-configs

   List "config" topics that are marked with the :rst:dir:`lsst-config-topic` directive that correspond to ``lsst.pex.config.Config``-types.

   **Options**

   ``root``
      The root Python package that configs must belong to to be including in the listing.
      For example, ``:root: lsst.pipe.tasks`` means that only configs in the ``lsst.pipe.tasks`` Python subpackage are included in the listing.

   ``toctree``
      If set, a :rst:dir:`toctree` is automatically generated for pages that appear in a given directory.
      For example, if configurable topics are in a ``configurables/`` subdirectory, set ``:toctree: configurables``.
      The :rst:dir:`toctree` is hidden.

      If this directive is listing topics that are already included by another :rst:dir:`toctree`, **don't set this option.**

      Note that ``toctree`` doesn't filter tasks using the same critera as the ``root`` option.
      Generally the directory structure should be set up so that ``toctree`` effectively corresponds to the filtering criteria set by ``root``, though.

   **Example:**

   .. code-block:: rst

      .. lsst-configs::
         :root: lsst.pipe.tasks
         :toctree: configs

Cross-reference roles
=====================

These roles link to task or config topic pages and to individual configuration fields.

- :rst:role:`lsst-task`
- :rst:role:`lsst-config`
- :rst:role:`lsst-config-field`

.. rst:role:: lsst-task

   Reference a task topic that is marked with the :rst:dir:`lsst-task-topic` directive.

   .. code-block:: rst

      :lsst-task:`lsst.pipe.tasks.processCcd.ProcessCcdTask`

   The link text can be shortened to just the task class name by prefixing the class with ``~``:

   .. code-block:: rst

      :lsst-task:`~lsst.pipe.tasks.processCcd.ProcessCcdTask`

   You can also provide alternative link text:

   .. code-block:: rst

      :lsst-task:`this task <lsst.pipe.tasks.processCcd.ProcessCcdTask>`

.. rst:role:: lsst-config

   Reference a standalone config topic that marked with the :rst:dir:`lsst-config-topic` directive.

   .. code-block:: rst

      :lsst-config:`lsst.pipe.tasks.colorterms.Colorterm`

   Abbreviate the link to just the class name:

   .. code-block:: rst

      :lsst-config:`~lsst.pipe.tasks.colorterms.Colorterm`

   Provide alternative link text:

   .. code-block:: rst

      :lsst-config:`this config <lsst.pipe.tasks.colorterms.Colorterm>`

.. rst:role:: lsst-config-field

   Reference a configuration field.

   Note that you must reference a configuration field as an attribute of a configuration class, not as an attribute of task class's ``config`` attribute.

   .. code-block:: rst

      :lsst-config-field:`lsst.pipe.tasks.processCcd.ProcessCcdConfig.isr`

   **See also:**

   The :rst:dir:`lsst-task-config-fields`, :rst:dir:`lsst-task-config-subtasks`, and :rst:dir:`lsst-config-fields` directives create the configuration field documentation that this role references.

Task interface directives
=========================

.. rst:directive:: .. lsst-task-api-summary:: task_name

   Generate a summary of the task's Python API.

   **Required argument:**

   - Name of the task class.

   **Example:**

   .. code-block:: rst

      .. lsst-task-api-summary:: lsst.pipe.tasks.assembleCoadd.AssembleCoaddTask
