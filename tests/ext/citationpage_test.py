# type: ignore
"""Tests for the build checks ``documenteer.ext.citationpage`` runs over a
``[[project.citations]]`` entry's ``page`` claim.

A claim is two halves — the docname of the page, and the fragment naming the
work within it — and each half can be wrong on its own. Both are checked as
the environment is checked for consistency, which is the first moment the
project's docnames and their doctrees are all available.

These builds compose ``html_context`` in :file:`conf.py` rather than through
:file:`documenteer.toml` and the pydata theme: what a check reads is the
environment, not the rendering, so the root is built out of the anchor shapes
a page can have. The full stack's build of the same extension is in
``tests/ext/guide_page_citations_test.py``.

Every test here builds into an srcdir of its own. The check runs only on a
build that re-reads a document, so a second build sharing a first one's srcdir
would report nothing at all and every assertion about silence would pass
without meaning anything.
"""

from __future__ import annotations

import pytest
from sphinx.testing.util import SphinxTestApp

from documenteer.citations import (
    Citation,
    CitationType,
    GuideCitation,
    OrganizationAuthor,
    PartialDate,
)

# The checks' type.subtype, as ``suppress_warnings`` spells it and as Sphinx
# appends it to the rendered message.
WARNING_NAME = "documenteer.citation_page"

# Must match the citations in tests/roots/test-citationpage/conf.py, and the
# anchors in the pages they claim.
EXPLICIT_LABEL = "Butler"
EXPLICIT_ANCHOR = "object-butler"
HEADING_LABEL = "TAP"
BAD_FRAGMENT_LABEL = "Renamed"
UNLABELLED_PAGE_LABEL = "Visit"
BAD_DOCNAME_LABEL = "Missing"


def _warnings(app: SphinxTestApp) -> list[str]:
    """Build the project and return its warnings, one per line."""
    app.build()
    return [
        line for line in app.warning.getvalue().splitlines() if line.strip()
    ]


def _warnings_naming(app: SphinxTestApp, label: str) -> list[str]:
    """Return the warnings naming one entry, so an assertion is scoped to the
    entry it is about rather than to the whole build's output.
    """
    return [line for line in _warnings(app) if f"{label!r}" in line]


def _warning_naming(app: SphinxTestApp, label: str) -> str:
    """Return the one warning naming an entry, failing if there is not
    exactly one.
    """
    (warning,) = _warnings_naming(app, label)
    return warning


@pytest.mark.sphinx(
    "html", testroot="citationpage", srcdir="citationpage-fragment"
)
def test_fragment_naming_no_anchor_warns(app: SphinxTestApp) -> None:
    """A claim whose fragment names no anchor on the page it claims is
    reported, naming the citation, the fragment, and the docname.

    Nothing else says so: the page builds, and the URL registered against the
    DOI resolves to a location that page does not contain.
    """
    warning = _warning_naming(app, BAD_FRAGMENT_LABEL)

    assert "products#no-such-anchor" in warning
    assert "'no-such-anchor' is not an anchor on products" in warning
    assert f"[{WARNING_NAME}]" in warning, (
        "the warning must carry a type.subtype so that a -W build can "
        "suppress it by name"
    )


@pytest.mark.sphinx(
    "html", testroot="citationpage", srcdir="citationpage-recommends"
)
def test_fragment_warning_recommends_an_explicit_target(
    app: SphinxTestApp,
) -> None:
    """The warning asks for an explicit target rather than for a corrected
    heading anchor.

    A heading's anchor is generated from its text, so a DOI registered
    against one silently stops resolving the day someone rewords the heading
    — which is the failure this check exists to catch, and not one to
    recommend re-creating.
    """
    warning = _warning_naming(app, BAD_FRAGMENT_LABEL)

    assert ".. _no-such-anchor:" in warning
    assert "generated from its text" in warning


@pytest.mark.sphinx(
    "html", testroot="citationpage", srcdir="citationpage-explicit"
)
def test_fragment_matching_an_explicit_target_passes(
    app: SphinxTestApp,
) -> None:
    """A fragment naming an explicit ``.. _label:`` target is accepted, even
    though docutils propagates that target onto its section *after* the
    anchor generated from the heading's text.

    The claimed anchor is therefore neither the section's first id nor the
    one the table of contents records for it, which is what rules out
    checking the fragment against ``env.tocs``.
    """
    assert not _warnings_naming(app, EXPLICIT_LABEL)
    assert _warnings_naming(app, BAD_FRAGMENT_LABEL), (
        "the check must have run on this build, or the silence above says "
        "nothing about the claim it is asserted of"
    )


@pytest.mark.sphinx(
    "html", testroot="citationpage", srcdir="citationpage-heading"
)
def test_fragment_matching_a_generated_heading_anchor_passes(
    app: SphinxTestApp,
) -> None:
    """A fragment naming the anchor a heading generates from its own text is
    accepted, since it is a real anchor on the page.

    It is a fragile one to register a DOI against, which is what the warning
    on a *broken* fragment recommends away from, but a site that has one
    today is not told its build is wrong.
    """
    assert not _warnings_naming(app, HEADING_LABEL)
    assert _warnings_naming(app, BAD_FRAGMENT_LABEL), (
        "the check must have run on this build, or the silence above says "
        "nothing about the claim it is asserted of"
    )


@pytest.mark.sphinx(
    "html", testroot="citationpage", srcdir="citationpage-docname"
)
def test_fragment_on_a_missing_docname_warns_only_once(
    app: SphinxTestApp,
) -> None:
    """A claim whose docname the project does not contain is reported for the
    docname alone.

    The fragment names a location on a page that does not exist, so there is
    nothing further to say about it and nothing to check it against.
    """
    warning = _warning_naming(app, BAD_DOCNAME_LABEL)

    assert "not a document in this project" in warning
    assert "anchor" not in warning


@pytest.mark.sphinx(
    "html", testroot="citationpage", srcdir="citationpage-suggests"
)
def test_fragment_warning_names_the_pages_explicit_targets(
    app: SphinxTestApp,
) -> None:
    """The warning offers the explicit targets the claimed page records, and
    only those.

    Listing every anchor on the page would name each of its headings, which
    is noise on a long page and an invitation to register a DOI against
    exactly the kind of generated anchor this check exists to catch moving.
    """
    warning = _warning_naming(app, BAD_FRAGMENT_LABEL)

    assert f"Did you mean #{EXPLICIT_ANCHOR}?" in warning
    # The page's headings generate anchors of their own, and none of them is
    # offered.
    assert "#tap" not in warning


@pytest.mark.sphinx(
    "html", testroot="citationpage", srcdir="citationpage-nosuggestion"
)
def test_fragment_warning_suggests_nothing_without_explicit_targets(
    app: SphinxTestApp,
) -> None:
    """A claimed page that records no explicit target is reported without a
    suggestion, rather than with an empty or heading-filled one.
    """
    warning = _warning_naming(app, UNLABELLED_PAGE_LABEL)

    assert "is not an anchor on unlabelled" in warning
    assert "Did you mean" not in warning


@pytest.mark.sphinx(
    "html",
    testroot="citationpage",
    srcdir="citationpage-suppressed",
    confoverrides={"suppress_warnings": [WARNING_NAME]},
)
def test_fragment_warning_is_suppressible(app: SphinxTestApp) -> None:
    """The fragment warning is suppressible under the same name the docname
    warning is, so a site that knowingly claims an anchor it has not written
    yet keeps its warnings-as-errors build green.
    """
    assert not [line for line in _warnings(app) if "is not an anchor" in line]


def _tap_claim(doi: str) -> GuideCitation:
    """Compose an entry labelled "TAP" whose claim names an anchor no page
    carries, since only the naming in the warning is under test here.
    """
    return GuideCitation(
        citation=Citation(
            title=f"Catalog {doi}",
            type=CitationType.dataset,
            doi=doi,
            authors=(OrganizationAuthor(name="Vera C. Rubin Observatory"),),
            publisher="Vera C. Rubin Observatory",
            date=PartialDate(2025, 6, 30),
        ),
        label="TAP",
        bibtex_key=doi,
        page="products",
        page_fragment="no-such-anchor",
    )


@pytest.mark.sphinx(
    "html",
    testroot="citationpage",
    srcdir="citationpage-shared-label",
    confoverrides={
        "html_context": {
            "documenteer_citations": [
                _tap_claim("10.71929/rubin/3382539").to_html_context(),
                _tap_claim("10.71929/rubin/3382540").to_html_context(),
            ]
        }
    },
)
def test_entries_sharing_a_label_are_named_by_key(
    app: SphinxTestApp,
) -> None:
    """Two entries under one label are each named by their key as well, so a
    site whose products all display the word "TAP" still gets two warnings it
    can tell apart.
    """
    for key in ("10.71929/rubin/3382539", "10.71929/rubin/3382540"):
        (warning,) = [
            line for line in _warnings(app) if f"'TAP' ({key})" in line
        ]
        assert "is not an anchor on products" in warning
