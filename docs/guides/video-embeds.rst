###############
Embedded videos
###############

Videos and screencasts are a great way to show user interfaces in your documentation.
Rubin Observatory has a Vimeo account where we store our documentation and user support videos.
Rubin user guides have built-in directives, ``youtube`` and ``vimeo``, to embed video players into the documentation page.

Embedding a Vimeo video
=======================

To embed a Vimeo video, use the ``vimeo`` directive with the video ID as the argument:

.. tab-set::

   .. tab-item:: reStructuredText
      :sync: rst

      .. code-block:: rst

         .. vimeo:: 800911530

   .. tab-item:: markdown
      :sync: md

      .. code-block:: markdown

         :::vimeo 800911530

The video ID is the number at the end of the video URL.
For example, the video URL for the video with ID ``800911530`` is ``https://vimeo.com/800911530``.

Embedding a YouTube video
=========================

To embed a YouTube video, use the ``youtube`` directive with the video ID as the argument:

.. tab-set::

   .. tab-item:: reStructuredText
      :sync: rst

      .. code-block:: rst

         .. youtube:: yKqEDFvmYwY

   .. tab-item:: markdown
      :sync: md

      .. code-block:: markdown

         :::vimeo yKqEDFvmYwY

The video ID is the string at the end of the video URL.
For example, the video URL for the video with ID ``yKqEDFvmYwY`` is ``https://www.youtube.com/watch?v=yKqEDFvmYwY``.

More information
================

- `sphinxcontrib-youtube <https://sphinxcontrib-youtube.readthedocs.io/en/latest/index.html>`__ is the Sphinx extension used to embed YouTube and Vimeo videos. See this documentation for additional options for using this extension.
