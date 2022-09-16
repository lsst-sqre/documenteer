########################################
Organizing content in a Rubin user guide
########################################

Once your Sphinx project is :doc:`configured to use the Rubin user guide theme <configuration>`, the next step is to organize your content into pages and directories, and create links into those pages with Sphinx toctrees.
The HTML theme of Rubin user guides, based on `PyData Sphinx Theme`_, offers multiple layers of navigational UI.
Taking best advantage of that navigational UI requires specific considerations for how the Sphinx toctrees are structured.
This page describes the navigational architecture of the HTML theme and its relationship to Sphinx toctrees, and includes suggested layouts for common project types.

Navigational levels in the HTML theme
=====================================

The HTML theme provides four levels of navigation:

#. Sections, which appear in the header navigation area
#. Section segments, which appear as bold labels in the primary (right side) sidebar
#. Pages, which appear as links in the primary (right side) sidebar
#. Page sections, which appear as links in the secondary (left side) sidebar

Creating sections
=================

Sections are the *root* level |toctree| items in the homepage of your documenation project (the root-level :file:`index.rst` or :file:`index.md` file).
In this example, there are three sections (a user guide, a developer guide, and a change log):

.. code-block:: rst
   :caption: index.rst

   .. toctree::

      user-guide/index
      api
      dev/index
      changelog

You use separate |toctree| directives to organize the homepage.
Sections are still created from each root entry.
This example is functionally equivalent to the first example, above:

.. code-block:: rst
   :caption: index.rst

   .. toctree::

      user-guide/index

   .. toctree::
      api

   .. toctree::

      dev/index

   .. toctree::
      :hidden:

      changelog

Creating sections without adding content to the index page
----------------------------------------------------------

By default Sphinx |toctree| directives create content on the page.
Sometimes, you don't want that content on the homepage.
You can create a section in the header navigation without creating a visible link on the homepage by using the ``hidden`` option on the |toctree| directive.

This technique is commonly used for adding the change log as a section in software documentation.
Using a hidden |toctree| referencing a single page allows you to put the change log in the correct slot on the header navigation without creating an awkward entry on the homepage:

.. code-block:: rst
   :caption: index.rst

   .. toctree::
      :hidden:

      changelog

Naming sections
---------------

The names of sections are based on the **titles** (top-level heading) of the pages linked from the toctree on the homepage.

In the following example, the name of the section is ``Python API``:

.. code-block:: rst
   :caption: index.rst

   .. toctree::

      api

.. code-block:: rst
   :caption: api.rst

   ##########
   Python API
   ##########

   Page content...

To avoid overcrowding the navigation bar, these section names need to be kept very short (one to two words).

Designing sections
------------------

Sections are listed horizontally in the top navigation (for the desktop navigation experience), which limits the number of sections that can be displayed.
Making the section navigation useful requires you to carefully plan both the number of sections, and the lengths of those section.

As a guideline, expect to use 1 – 5 sections.
Therefore, your sections should be fairly broad, and shouldn't need to grow in number as the project grows.
For example, a common sectioning pattern for open source Python projects is:

- User guide
- API reference
- Change log
- Contributing

These sections are oriented around content type and audience.
The sections are designed so that users can easily see all user-oriented documentation, and documentation for contributors is purposefully sequestered to avoid audience confusion.
Since the API reference and change log documentation are common topics, those are also available as sections.
Further, any new content could fall into one of these sections, making this a future-proof organization.

A different strategy is to organize sections around features.
This works well if there are a small number of distinct features, and those features are orthogonal from each other.
For example, the Documenteer documentation has sections for supporting Rubin's distinct documentation configurations (user guides, technical notes, and Science Pipelines / EUPS stack documentation), along with a section for the Sphinx extensions, the change log, and a developer's guide.
This is a potentially risky architecture, because new feature categories could break the navigational design.
However, it creates a clean and bespoke documentation experience when pulled off well.

The theme provides an escape valve for overcrowded navigation bars by collecting excess sections into a "More" drop-down.
This drop down can be used to collect little-used sections, or more internally-oriented sections such as development documentation.
You can set the number of sections that appear in the navigation bar *before* the "More" button with the :ref:`sphinx.theme.header_links_before_dropdown <guide-project-header-links-before-dropdown>` configuration.

Creating section navigation and segments
========================================

The navigation for a section is presented in the primary sidebar, to the left of the content.
A section's content is based on the |toctree| items linked from the root page of the section (this is the page linked from a |toctree| on the root page of the site, usually :file:`index.rst`).

Section segments
----------------

Sections commonly have a large number of pages.
You might want to want to group those sections into segments around themes of content types.
You can do this by setting a ``caption`` argument on separate |toctree| directives for each segment.

.. code-block:: rst
   :caption: section/index.rst

   .. toctree::

      overview

   .. toctree::
      :caption: Tutorials

      tutorial-a
      tutorial-b

    .. toctree::
       :caption: Guides

       guide-a
       guide-b
       guide-c

In this above example, the "Overview" page appears first in the section navigation, followed by a segment named "Tutorials" listing two tutorials, followed by another segment named "Guides" listing three guides.

Note that on the root page, those captions appear as headings.

Hierarchical navigation
-----------------------

If the pages you link from the root page of a section also include |toctree| directives, those pages will appear hierarchically under that page in the primary sidebar.

Although a flat navigational schema is generally recommended, a hierarchical approach can make sense in larger documentation sites.

Suggested layouts
=================

These are suggested section layouts for common types of Rubin Observatory documentation projects.
Larger user guides often require bespoke design.

Python library
--------------

.. tab-set::

   .. tab-item:: Sections

      - User guide
      - Python API
      - Change log
      - Developer guide

   .. tab-item:: index.rst

       .. code-block:: rst

          User guide
          ==========

          .. toctree::

             user-guide/index

          Python API
          ==========

          .. toctree::

             api

          .. toctree::
             :hidden:

             changelog

          Developer guide
          ===============

          .. toctree::

             dev/index

Web service
-----------

.. tab-set::

   .. tab-item:: Sections

      - User guide
      - API
      - Operations
      - Change log
      - Development
