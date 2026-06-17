// Localize documenteer.ext.lastmodified's "last modified" footer date.
//
// The footer renders the page's Git commit date as a <time> element whose
// datetime attribute carries the canonical UTC ISO 8601 timestamp and whose
// visible text is the UTC date (YYYY-MM-DD) as a no-JavaScript fallback. This
// script rewrites that text to the reader's own local date in a long-month
// style (for example "June 1, 2024"), so a UTC date that lands on a different
// calendar day than the reader's is shown correctly for the reader.
//
// On any parse failure or invalid date the UTC fallback text is left intact.
(function () {
  'use strict';

  function localize() {
    var elements = document.querySelectorAll(
      'time[data-documenteer-last-modified]'
    );
    for (var i = 0; i < elements.length; i++) {
      var element = elements[i];
      var iso = element.getAttribute('datetime');
      if (!iso) {
        continue;
      }
      try {
        var date = new Date(iso);
        if (isNaN(date.getTime())) {
          continue;
        }
        element.textContent = date.toLocaleDateString(undefined, {
          year: 'numeric',
          month: 'long',
          day: 'numeric',
        });
      } catch (error) {
        // Leave the UTC fallback text untouched.
      }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', localize);
  } else {
    localize();
  }
})();
