# type: ignore
"""Tests for the ``doi`` role.

The role links one of the site's ``[[project.citations]]`` entries inline,
wherever a sentence, a bullet, or a table cell needs the DOI rather than the
whole citation. It reads the same ``html_context`` the ``citation-card``
directive does, so these tests build the same minimal project (see
:file:`tests/roots/test-citationcard/conf.py`) and vary it with confoverrides.

The srcdirs here are distinct from the ones
:file:`tests/ext/citationcard_test.py` uses: a role's warning is emitted while
a page is *read*, so a build that shares a cached doctree with another module's
build would not emit it again.
"""

from __future__ import annotations

import pytest
from docutils import nodes
from lxml import html
from sphinx.testing.util import SphinxTestApp

# Must match tests/roots/test-citationcard/conf.py.
DATASET_DOI_URL = "https://doi.org/10.5281/zenodo.10385500"
SOFTWARE_URL = "https://github.com/lsst-sqre/documenteer"
# The entry whose BibTeX key is pinned, so that selecting by key selects
# something no spelling of a DOI does.
REPORT_DOI_URL = "https://doi.org/10.71929/rubin/2570309"

# The warning's type.subtype, as ``suppress_warnings`` spells it and as Sphinx
# appends it to the rendered message. It is the ``citation-card`` directive's
# subtype: the two surfaces read one configuration, so a site suppresses their
# warnings as one name.
WARNING_NAME = "documenteer.citation_card"


def _page(app: SphinxTestApp, name: str) -> html.HtmlElement:
    """Build the project and parse one of its pages."""
    app.build()
    return html.fromstring(
        (app.outdir / f"{name}.html").read_text(encoding="utf-8")
    )


def _section(doc: html.HtmlElement, section_id: str) -> html.HtmlElement:
    """Return the page section with this id, so an assertion is scoped to the
    one example it is about rather than to the whole rendered page.
    """
    (section,) = doc.cssselect(f"section#{section_id}")
    return section


def _links(element: html.HtmlElement) -> list[html.HtmlElement]:
    """Return the element's hyperlinks, minus the heading anchor Sphinx adds
    to every section title.
    """
    return [
        link
        for link in element.cssselect("a")
        if "headerlink" not in (link.get("class") or "")
    ]


def _text(element: html.HtmlElement) -> str:
    """Return the element's text content, with whitespace collapsed."""
    return " ".join(element.text_content().split())


@pytest.mark.sphinx("html", testroot="citationcard", srcdir="citationdoi")
def test_role_links_the_dois_resolvable_url(app: SphinxTestApp) -> None:
    """``:doi:`Dataset``` renders the entry's DOI as a link whose text is the
    resolvable ``https://doi.org/`` URL.

    Displaying the DOI in its resolvable form, rather than bare or as the
    entry's label, is what the Crossref/DataCite display guidelines ask for.
    """
    section = _section(_page(app, "roles"), "prose")

    (link,) = _links(section)
    assert link.get("href") == DATASET_DOI_URL
    assert _text(link) == DATASET_DOI_URL
    assert _text(section.cssselect("p")[0]) == (
        f"The dataset is published as {DATASET_DOI_URL}."
    )
    # A doi.org URL leaves the site, so the link is external: Sphinx would
    # otherwise try to resolve it as a reference within the project.
    assert "external" in link.get("class").split()


@pytest.mark.sphinx("html", testroot="citationcard", srcdir="citationdoi")
def test_role_takes_custom_link_text(app: SphinxTestApp) -> None:
    """``:doi:`text <Label>``` puts the author's own words on the link, so a
    sentence that reads as prose still resolves through the DOI.
    """
    section = _section(_page(app, "roles"), "custom-text")

    (link,) = _links(section)
    assert link.get("href") == DATASET_DOI_URL
    assert _text(link) == "the dataset release"


@pytest.mark.sphinx("html", testroot="citationcard", srcdir="citationdoi")
def test_role_selects_an_entry_by_bibtex_key(app: SphinxTestApp) -> None:
    """``:doi:`RTN-115``` links the entry whose BibTeX key is ``RTN-115``.

    The role resolves a selector through the same lookup the directive does,
    so a page that selects a card by key selects the same entry inline.
    """
    section = _section(_page(app, "selectors"), "role-by-key")

    (link,) = _links(section)
    assert link.get("href") == REPORT_DOI_URL
    assert _text(link) == REPORT_DOI_URL


@pytest.mark.sphinx("html", testroot="citationcard", srcdir="citationdoi")
def test_role_selects_an_entry_by_doi(app: SphinxTestApp) -> None:
    """A DOI selects its entry as a role target too, in any spelling."""
    section = _section(_page(app, "selectors"), "role-by-doi")

    (link,) = _links(section)
    assert link.get("href") == DATASET_DOI_URL
    assert _text(link) == DATASET_DOI_URL


@pytest.mark.sphinx("html", testroot="citationcard", srcdir="citationdoi")
def test_role_takes_a_doi_target_with_custom_text(
    app: SphinxTestApp,
) -> None:
    """The explicit-title spelling takes a DOI as its target, which is what
    lets a page display a short word over an entry it selects unambiguously.

    Forty products each with a TAP entry cannot each be labelled "TAP" *and*
    be selected by label; selecting by DOI is what frees the label to say what
    the reader needs at that spot.
    """
    section = _section(_page(app, "selectors"), "role-by-doi-with-custom-text")

    (link,) = _links(section)
    assert link.get("href") == DATASET_DOI_URL
    assert _text(link) == "the dataset release"


# Its own srcdir: a role's warning is emitted while a page is *read*, so a
# test that asserts on one needs a build that has not already cached the
# page's doctree from an earlier test.
@pytest.mark.sphinx(
    "html", testroot="citationcard", srcdir="citationdoi-unknown"
)
def test_unknown_selector_warns_and_leaves_readable_text(
    app: SphinxTestApp,
) -> None:
    """A target no entry answers to warns, in the words the directive uses,
    and renders the target as unlinked text.

    The build still succeeds: a citation a page names should never be the
    reason the site fails to build, and the sentence around the role has to
    stay readable in the page that ships.
    """
    section = _section(_page(app, "role-warnings"), "unknown-label")

    assert not _links(section)
    assert _text(section.cssselect("p")[0]) == (
        "The catalog is published as Nonesuch."
    )
    assert not section.cssselect(".system-message"), (
        "the role must not leave a system message in the page"
    )

    (warning,) = [
        line
        for line in app.warning.getvalue().splitlines()
        if "Nonesuch" in line and "doi role:" in line
    ]
    assert 'no citation matches "Nonesuch"' in warning
    assert "label, its BibTeX key, or its DOI" in warning
    assert "veracrubinobservatory2025citation (Site)" in warning
    assert f"[{WARNING_NAME}]" in warning, (
        "the warning must carry a type.subtype so that a -W build can "
        "suppress it by name"
    )


@pytest.mark.sphinx(
    "html", testroot="citationcard", srcdir="citationdoi-ambiguous"
)
def test_shared_label_warns_and_leaves_readable_text(
    app: SphinxTestApp,
) -> None:
    """A target two entries answer to warns and renders unlinked text, the
    same way an unresolvable one does.

    The role mirrors the card: ambiguity is reported rather than guessed at,
    since either answer would be the wrong DOI in some sentence with nothing
    on the page to say so.
    """
    section = _section(_page(app, "repeated-labels"), "role-by-shared-label")

    assert not _links(section)
    assert _text(section.cssselect("p")[0]) == (
        "The catalog is published as TAP."
    )

    warnings = app.warning.getvalue()
    assert '"TAP" matches 2' in warnings
    assert "10.71929/rubin/3382539" in warnings
    assert "10.71929/rubin/3382540" in warnings
    assert f"[{WARNING_NAME}]" in warnings


@pytest.mark.sphinx(
    "html", testroot="citationcard", srcdir="citationdoi-nodoi"
)
def test_entry_without_a_doi_warns_rather_than_linking_its_url(
    app: SphinxTestApp,
) -> None:
    """An entry located by ``url`` rather than by a DOI warns and renders
    unlinked text; the role never links the ``url`` under its own name.

    The role's name is its contract. In the default spelling the link's text
    *is* the DOI, so linking a repository URL here would display that URL as
    though it were one, and a reader following a ``:doi:`` link expects to
    arrive at a DOI either way. The warning names the entry the way every
    other citation warning names one -- rather than by the text the role
    wrote, which may have been a key -- and it names the entry's url, which is
    what an author writes an ordinary hyperlink to instead.
    """
    section = _section(_page(app, "role-warnings"), "located-by-url")

    assert not _links(section)
    assert _text(section.cssselect("p")[0]) == (
        "The package is published as Software."
    )
    assert SOFTWARE_URL not in html.tostring(section, encoding="unicode")

    warnings = app.warning.getvalue()
    assert "the citation 'Software' declares no DOI" in warnings
    assert SOFTWARE_URL in warnings, (
        "the warning names the url the author can link by hand instead"
    )
    assert f"[{WARNING_NAME}]" in warnings


@pytest.mark.sphinx("html", testroot="citationcard", srcdir="citationdoi")
def test_role_composes_wherever_inline_markup_does(
    app: SphinxTestApp,
) -> None:
    """The role works in a bullet, a table cell, and the body of a
    substitution definition.

    These are the uses a block-level directive cannot serve, and the reason
    the role exists: a product page's access list, a table of products, and
    the ``|name|`` substitutions a site writes to reuse one reference.
    """
    doc = _page(app, "roles")

    (bullet,) = _section(doc, "bullet").cssselect("li")
    assert _text(bullet) == f"DOI: {DATASET_DOI_URL}"
    assert _links(bullet)[0].get("href") == DATASET_DOI_URL

    cell = _section(doc, "table").cssselect("tbody td")[1]
    assert _links(cell)[0].get("href") == DATASET_DOI_URL

    section = _section(doc, "substitution")
    (link,) = _links(section)
    assert link.get("href") == DATASET_DOI_URL
    assert _text(section.cssselect("p")[-1]) == (
        "The images and catalogs are described by the dataset."
    )


@pytest.mark.sphinx("html", testroot="citationcard", srcdir="citationdoi")
def test_role_reaches_a_myst_document(app: SphinxTestApp) -> None:
    """A MyST page spells the role ``{doi}`` and gets the same link.

    Rubin guides are written in both markups, so a reference that only worked
    in reStructuredText would leave the Markdown half of a site writing the
    URL by hand.
    """
    doc = _page(app, "roles-myst")

    (link,) = _links(_section(doc, "myst-prose"))
    assert link.get("href") == DATASET_DOI_URL
    assert _text(link) == DATASET_DOI_URL

    (titled,) = _links(_section(doc, "myst-custom-text"))
    assert titled.get("href") == DATASET_DOI_URL
    assert _text(titled) == "the dataset release"


@pytest.mark.sphinx(
    "html",
    testroot="citationcard",
    srcdir="citationdoi-nocitations",
    confoverrides={"html_context": {}},
)
def test_site_without_citations_warns_once_per_use(
    app: SphinxTestApp,
) -> None:
    """A site that declares no citations warns once for each use of the role,
    in the same words the ``citation-card`` directive uses.

    Once per use rather than once per site: each warning is located at the
    markup that has to change, and an author fixing them wants to see all of
    them rather than the first.
    """
    section = _section(_page(app, "roles"), "prose")
    assert not _links(section)

    warnings = app.warning.getvalue().splitlines()
    from_roles = [
        line
        for line in warnings
        if "roles.rst" in line and "declares no citations" in line
    ]
    assert len(from_roles) == 5, (
        "roles.rst uses the role five times: in prose, with custom text, in "
        "a bullet, in a table cell, and in a substitution definition"
    )
    assert "[[project.citations]]" in from_roles[0]
    assert f"[{WARNING_NAME}]" in from_roles[0]


@pytest.mark.sphinx(
    "html", testroot="citationcard", srcdir="citationdoi-shortlink"
)
def test_role_link_resists_a_link_shortener(
    app: SphinxTestApp, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The role builds its link in the shape pydata-sphinx-theme's
    ``ShortenLinkTransform`` leaves alone, so the DOI reaches the reader whole.

    The transform rewrites a link whose sole child is a bare ``Text`` equal to
    its ``refuri`` into ``org/repo``, which would turn a displayed DOI into
    something a reader cannot copy into a bibliography. doi.org is not one of
    the hosts it shortens today, so this test registers it as one: what is
    pinned is the shape of the role's link, not the theme's current host list.
    """
    short_link = pytest.importorskip(
        "pydata_sphinx_theme.short_link",
        reason="pydata_sphinx_theme is not installed",
    )
    transform = short_link.ShortenLinkTransform

    monkeypatch.setitem(transform.supported_platform, "doi.org", "github")
    app.build()
    doctree = app.env.get_doctree("roles")

    # The shape the role used to build, kept as a control: it proves the
    # transform really does rewrite a doi.org link under this monkeypatch, so
    # that the assertions below cannot pass vacuously.
    control = nodes.reference(
        "", DATASET_DOI_URL, refuri=DATASET_DOI_URL, internal=False
    )
    doctree += nodes.paragraph("", "", control)

    transform(doctree).run()

    assert control.astext() != DATASET_DOI_URL
    assert "github" in control["classes"]

    links = [
        node
        for node in doctree.findall(nodes.reference)
        if node.get("refuri") == DATASET_DOI_URL and node is not control
    ]
    assert links, "roles.rst links the Dataset DOI"
    for link in links:
        assert "github" not in link["classes"]
    # Only the role's default spelling displays the DOI itself; the custom-text
    # spellings display the author's words, which the transform never touched.
    assert any(link.astext() == DATASET_DOI_URL for link in links)
