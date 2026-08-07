// Align the Rubin page footer (rubin-footer.html) with the article column.
//
// The theme's .bd-footer spans the full page width below the sidebars, while
// the article column's left edge varies per page: the primary sidebar's
// width (when present) plus the centering slack of the article container
// inside .bd-content. That edge can't be expressed in static CSS without
// hard-coding the theme's layout math, so this script measures the rendered
// article text box (.bd-article's content box) and left-aligns the footer
// content to it, matching its measure.
//
// The centered max-width layout in rubin-pydata-theme.css is the
// no-JavaScript fallback and stays in effect until this script runs. A
// ResizeObserver keeps the alignment in sync by watching <body> (viewport
// resizes, font-load reflows), the primary sidebar (the theme's collapse
// button squeezes its width without changing the body's size — and when
// the article column is at its max-width cap it only moves, so neither
// body nor article resize), and the article itself (content-driven
// reflows). The observer settles because re-applying identical styles
// does not trigger new layout changes; during the sidebar's squeeze
// transition it fires per animation frame, tracking the moving layout.
(function () {
  'use strict';

  function align() {
    var article = document.querySelector('.bd-main .bd-article');
    var footer = document.querySelector('.bd-footer .rubin-footer');
    if (!article || !footer || !footer.parentElement) {
      return;
    }
    var articleRect = article.getBoundingClientRect();
    var articleStyle = window.getComputedStyle(article);
    var paddingLeft = parseFloat(articleStyle.paddingLeft) || 0;
    var paddingRight = parseFloat(articleStyle.paddingRight) || 0;
    var textLeft = articleRect.left + paddingLeft;
    var textWidth = articleRect.width - paddingLeft - paddingRight;
    var parentRect = footer.parentElement.getBoundingClientRect();
    // The stylesheet's margin-inline: auto still supplies the right margin;
    // only the left margin is pinned, so leftover space stays on the right.
    footer.style.marginLeft = Math.max(0, textLeft - parentRect.left) + 'px';
    footer.style.maxWidth = textWidth + 'px';
  }

  function start() {
    align();
    if ('ResizeObserver' in window) {
      var observer = new ResizeObserver(align);
      observer.observe(document.body);
      var sidebar = document.querySelector('.bd-sidebar-primary');
      if (sidebar) {
        observer.observe(sidebar);
      }
      var article = document.querySelector('.bd-main .bd-article');
      if (article) {
        observer.observe(article);
      }
    } else {
      window.addEventListener('resize', align);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
})();
