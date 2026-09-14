// Copy a citation's BibTeX entry to the clipboard.
//
// Every citation surface Documenteer renders -- the card the citation-card
// directive renders (documenteer.ext.citationcard) and the citations in a
// user guide's page footer (rubin-footer.html), and the Cite section of a
// technote's sidebar (components/sidebar-citation.html) -- puts the entry in
// a collapsed <details> alongside a button. This script is what makes the
// button work.
//
// The entry lives in the <details>'s <pre> and nowhere else: reading the text
// from there rather than from a duplicated data- attribute means what is
// copied is exactly what the reader sees, and it is also what keeps the entry
// selectable on a page this script never reaches. So the no-JavaScript
// fallback is the markup itself, and a browser without the asynchronous
// clipboard API (or one that withholds it outside a secure context) has its
// buttons removed rather than left to do nothing when pressed.
(function () {
  'use strict';

  // Each surface names its parts under its own block class; only these
  // hooks are shared.
  var BUTTONS =
    '.documenteer-citation-card__copy, ' +
    '.rubin-footer__citation-copy, ' +
    '.technote-sidebar-citation__copy';
  var STATUSES =
    '.documenteer-citation-card__copy-status, ' +
    '.rubin-footer__citation-copy-status, ' +
    '.technote-sidebar-citation__copy-status';

  var COPIED_LABEL = 'Copied';
  var FAILED_LABEL = 'Press Ctrl+C to copy';
  // Long enough to read the confirmation, short enough that the button is
  // back to its own label before the reader looks for it again.
  var RESET_DELAY_MS = 2000;

  function partOf(button, selector) {
    return button.parentElement
      ? button.parentElement.querySelector(selector)
      : null;
  }

  function wire(button) {
    var entry = partOf(button, 'pre');
    if (!entry) {
      return;
    }
    // The live region announces the outcome: swapping the button's own label
    // is silent to a screen reader that is not focused on it.
    var status = partOf(button, STATUSES);
    var label = button.textContent;
    var timer = null;

    function report(text) {
      button.textContent = text;
      if (status) {
        status.textContent = text;
      }
      if (timer !== null) {
        window.clearTimeout(timer);
      }
      timer = window.setTimeout(function () {
        button.textContent = label;
        if (status) {
          status.textContent = '';
        }
        timer = null;
      }, RESET_DELAY_MS);
    }

    button.addEventListener('click', function () {
      navigator.clipboard.writeText(entry.textContent).then(
        function () {
          report(COPIED_LABEL);
        },
        function () {
          // A clipboard write can be refused (a permissions policy, a
          // gesture the browser did not count). Saying so points the reader
          // at the <pre>, which is still there to select.
          report(FAILED_LABEL);
        }
      );
    });
  }

  function discard(button) {
    var status = partOf(button, STATUSES);
    if (status && status.parentNode) {
      status.parentNode.removeChild(status);
    }
    if (button.parentNode) {
      button.parentNode.removeChild(button);
    }
  }

  function start() {
    var supported = !!(
      window.navigator &&
      navigator.clipboard &&
      navigator.clipboard.writeText
    );
    var buttons = document.querySelectorAll(BUTTONS);
    Array.prototype.forEach.call(buttons, supported ? wire : discard);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
})();
