"""Tests for the documenteer.citations module."""

from __future__ import annotations

import datetime
import importlib
import importlib.util
import json

import pytest

from documenteer.citations import (
    BibtexEntryType,
    Citation,
    CitationType,
    GuideCitation,
    OrganizationAuthor,
    PartialDate,
    PersonAuthor,
    compose_landing_page_jsonld,
    compose_page_jsonld,
    doi_url,
    normalize_doi,
    orcid_url,
    ror_url,
)


@pytest.mark.parametrize(
    "value",
    [
        "10.5281/zenodo.10385500",
        "doi:10.5281/zenodo.10385500",
        "doi: 10.5281/zenodo.10385500",
        "doi:  10.5281/zenodo.10385500",
        "DOI:10.5281/zenodo.10385500",
        "https://doi.org/10.5281/zenodo.10385500",
        "http://doi.org/10.5281/zenodo.10385500",
        "https://dx.doi.org/10.5281/zenodo.10385500",
        "http://dx.doi.org/10.5281/zenodo.10385500",
        "https://doi.org/ 10.5281/zenodo.10385500",
        "  10.5281/zenodo.10385500  ",
        "10.5281/zenodo.10385500\n",
    ],
)
def test_normalize_doi_accepts_spellings(value: str) -> None:
    assert normalize_doi(value) == "10.5281/zenodo.10385500"


@pytest.mark.parametrize(
    "value",
    [
        "",
        "not-a-doi",
        "10.5281",
        "10.5281/",
        "11.5281/zenodo.10385500",
        "10.52/zenodo.10385500",
        "https://doi.org/not-a-doi",
        "10.5281/zenodo 10385500",
    ],
)
def test_normalize_doi_rejects_malformed(value: str) -> None:
    with pytest.raises(ValueError, match="Not a DOI"):
        normalize_doi(value)


# Whether the technote extra is installed; the parity test below compares
# Documenteer's DOI normalizer against technote's own.
_HAS_TECHNOTE = importlib.util.find_spec("technote") is not None

# The DOI spellings Documenteer and technote must agree on: every prefix,
# the whitespace a hand-edited technote.toml carries between a prefix and
# the identifier, and values both must reject. technote's normalizer
# validates ``[technote] doi`` when technote.toml is parsed; Documenteer's
# runs for a guide's ``[[project.citations]]``, for ``documenteer technote
# sync-cff``, and for the technote linter — paths that never construct
# technote's TOML model.
DOI_PARITY_SPELLINGS = [
    "10.5281/zenodo.10385500",
    "doi:10.5281/zenodo.10385500",
    "doi: 10.5281/zenodo.10385500",
    "doi:  10.5281/zenodo.10385500",
    "DOI:10.5281/zenodo.10385500",
    "https://doi.org/10.5281/zenodo.10385500",
    "http://doi.org/10.5281/zenodo.10385500",
    "https://dx.doi.org/10.5281/zenodo.10385500",
    "http://dx.doi.org/10.5281/zenodo.10385500",
    "https://doi.org/ 10.5281/zenodo.1",
    "  10.5281/zenodo.10385500  ",
    "10.5281/zenodo.10385500\n",
    "10.71929",
    "not-a-doi",
    "",
]


@pytest.mark.skipif(
    not _HAS_TECHNOTE, reason="the technote extra is not installed"
)
@pytest.mark.parametrize("value", DOI_PARITY_SPELLINGS)
def test_normalize_doi_matches_technote(value: str) -> None:
    """Documenteer's normalizer returns the same bare DOI as technote's, and
    accepts and rejects the same spellings, so that a technote.toml which
    builds also passes the linter and sync-cff.
    """
    technote_doi = importlib.import_module("technote.metadata.doi")

    try:
        expected = technote_doi.normalize_doi(value)
    except ValueError:
        with pytest.raises(ValueError, match="Not a DOI"):
            normalize_doi(value)
    else:
        assert normalize_doi(value) == expected


def test_doi_url_normalizes_first() -> None:
    assert (
        doi_url("doi:10.5281/zenodo.10385500")
        == "https://doi.org/10.5281/zenodo.10385500"
    )


def test_citation_normalizes_its_doi() -> None:
    citation = Citation(
        doi="https://doi.org/10.71929/rubin/2570308",
        title="Data Preview 2",
        authors=(OrganizationAuthor(name="Vera C. Rubin Observatory"),),
        publisher="Vera C. Rubin Observatory",
        date=PartialDate(2025, 6, 30),
        url="https://dp2.lsst.io/",
    )
    assert citation.doi == "10.71929/rubin/2570308"
    assert citation.doi_url == "https://doi.org/10.71929/rubin/2570308"


def test_citation_without_a_doi_has_no_doi_url() -> None:
    citation = Citation(
        title="Data Preview 2",
        authors=(PersonAuthor(family_name="Sick", given_name="Jonathan"),),
    )
    assert citation.doi is None
    assert citation.doi_url is None


def test_citation_rejects_a_malformed_doi() -> None:
    with pytest.raises(ValueError, match="Not a DOI"):
        Citation(doi="not-a-doi", title="Data Preview 2")


@pytest.mark.parametrize(
    ("family_name", "citation_name", "bibtex_name"),
    [
        # Rubin's own DataCite records credit the Survey Cadence
        # Optimization Committee as a Personal creator carrying a family
        # name and no given name. The braces are what stop a style from
        # reading "Survey Cadence Optimization" as given names and
        # abbreviating them.
        (
            "Survey Cadence Optimization Committee",
            "Survey Cadence Optimization Committee",
            "{Survey Cadence Optimization Committee}",
        ),
        # A mononym is a legitimate personal name, not a degenerate one.
        # Braces around it are inert, so the branch does not special-case it.
        ("Aristotle", "Aristotle", "{Aristotle}"),
        # The BibTeX spelling is escaped and collapsed on this branch just
        # as it is on the given-plus-family one, so the doubled space a
        # hand-edited source carries never reaches the entry.
        ("Ekstrøm  Reyes", "Ekstrøm  Reyes", "{Ekstrøm Reyes}"),
    ],
)
def test_person_author_without_a_given_name(
    family_name: str, citation_name: str, bibtex_name: str
) -> None:
    """A person credited by family name alone composes as that name in both
    spellings, with no separator left where a given name would go, and the
    BibTeX spelling braces it so that BibTeX reads it as one whole name.
    """
    author = PersonAuthor(family_name=family_name)
    assert author.citation_name == citation_name
    assert author.bibtex_name == bibtex_name


def dataset_citation() -> Citation:
    """Build a dataset citation credited to an organization."""
    return Citation(
        doi="10.71929/rubin/2570308",
        title="Data Preview 2",
        authors=(OrganizationAuthor(name="Vera C. Rubin Observatory"),),
        publisher="Vera C. Rubin Observatory",
        date=PartialDate(2025, 6, 30),
        url="https://dp2.lsst.io/",
    )


def technote_citation() -> Citation:
    """Build a technote citation credited to several people."""
    return Citation(
        doi="10.5281/zenodo.10385500",
        title="Citations in Documenteer",
        authors=(
            PersonAuthor(
                family_name="Sick",
                given_name="Jonathan",
                orcid="https://orcid.org/0000-0003-3001-676X",
            ),
            PersonAuthor(family_name="Jones", given_name="R. Lynne"),
        ),
        publisher="Vera C. Rubin Observatory",
        date=PartialDate(2026, 8, 24),
        url="https://sqr-000.lsst.io/",
        number="SQR-000",
    )


def test_plain_text_for_an_organization_author() -> None:
    assert dataset_citation().to_plain_text() == (
        "Vera C. Rubin Observatory (2025). Data Preview 2. "
        "Vera C. Rubin Observatory. https://doi.org/10.71929/rubin/2570308"
    )


def test_plain_text_for_multiple_person_authors() -> None:
    assert technote_citation().to_plain_text() == (
        "Sick, Jonathan; Jones, R. Lynne (2026). Citations in Documenteer. "
        "Vera C. Rubin Observatory. https://doi.org/10.5281/zenodo.10385500"
    )


def test_plain_text_omits_missing_segments() -> None:
    citation = Citation(title="Data Preview 2", url="https://dp2.lsst.io/")
    assert citation.to_plain_text() == "Data Preview 2. https://dp2.lsst.io/"


def test_plain_text_omits_a_blank_title() -> None:
    """A whitespace-only segment is collapsed before it is filtered, so it is
    dropped rather than composed as a stray bare period.
    """
    citation = Citation(title=" ", url="https://example.org/x")
    assert citation.to_plain_text() == "https://example.org/x"


def test_plain_text_omits_a_blank_publisher() -> None:
    citation = Citation(
        title="Real Title", publisher="   ", url="https://example.org/x"
    )
    assert citation.to_plain_text() == "Real Title. https://example.org/x"


def test_plain_text_omits_a_blank_author() -> None:
    citation = Citation(
        title="Real Title",
        authors=(PersonAuthor(family_name="   "),),
        url="https://example.org/x",
    )
    assert citation.to_plain_text() == "Real Title. https://example.org/x"


def test_plain_text_omits_a_blank_url() -> None:
    """A blank landing page is absent rather than trailing whitespace."""
    citation = Citation(title="Real Title", url="   ")
    assert citation.location is None
    assert citation.to_plain_text() == "Real Title."


def test_bibtex_misc_for_an_organization_author() -> None:
    assert dataset_citation().to_bibtex() == (
        "@misc{veracrubinobservatory2025data,\n"
        "    author = {{Vera C. Rubin Observatory}},\n"
        "    title = {{Data Preview 2}},\n"
        "    year = {2025},\n"
        "    publisher = {Vera C. Rubin Observatory},\n"
        "    doi = {10.71929/rubin/2570308},\n"
        "    url = {https://dp2.lsst.io/}\n"
        "}"
    )


def test_bibtex_techreport_for_multiple_person_authors() -> None:
    assert technote_citation().to_bibtex(
        entry_type=BibtexEntryType.techreport
    ) == (
        "@techreport{sick2026citations,\n"
        "    author = {Sick, Jonathan and Jones, R. Lynne},\n"
        "    title = {{Citations in Documenteer}},\n"
        "    year = {2026},\n"
        "    institution = {Vera C. Rubin Observatory},\n"
        "    number = {SQR-000},\n"
        "    doi = {10.5281/zenodo.10385500},\n"
        "    url = {https://sqr-000.lsst.io/}\n"
        "}"
    )


def test_composers_credit_a_family_only_author() -> None:
    """A citation credited to a person who has only a family name composes
    through both composers without the separator a ``Family, Given``
    spelling would leave behind, and keys off that family name alone.

    The BibTeX entry braces the name, as it does an organization's, so that
    a style renders the committee's name whole instead of abbreviating
    "Survey Cadence Optimization" as though it were a string of given names.
    """
    citation = Citation(
        doi="10.71929/rubin/2570308",
        title="Survey Cadence Optimization",
        authors=(
            PersonAuthor(family_name="Survey Cadence Optimization Committee"),
        ),
        date=PartialDate(2025, 6, 30),
    )
    assert citation.to_plain_text() == (
        "Survey Cadence Optimization Committee (2025). "
        "Survey Cadence Optimization. "
        "https://doi.org/10.71929/rubin/2570308"
    )
    assert citation.to_bibtex() == (
        "@misc{surveycadenceoptimizationcommittee2025survey,\n"
        "    author = {{Survey Cadence Optimization Committee}},\n"
        "    title = {{Survey Cadence Optimization}},\n"
        "    year = {2025},\n"
        "    doi = {10.71929/rubin/2570308},\n"
        "    url = {https://doi.org/10.71929/rubin/2570308}\n"
        "}"
    )


def test_bibtex_escapes_latex_reserved_characters() -> None:
    citation = Citation(
        title=r"C^2 {braces} \path ~tilde $math# _under & 100%",
        authors=(OrganizationAuthor(name="A & B"),),
    )
    assert citation.to_bibtex() == (
        "@misc{abc2,\n"
        "    author = {{A \\& B}},\n"
        "    title = {{C\\textasciicircum{}2 \\{braces\\} "
        "\\textbackslash{}path \\textasciitilde{}tilde \\$math\\# "
        "\\_under \\& 100\\%}}\n"
        "}"
    )


def test_bibtex_accepts_an_explicit_key() -> None:
    assert (
        technote_citation()
        .to_bibtex(key="SQR-000")
        .startswith("@misc{SQR-000,\n")
    )


def test_bibtex_misc_entry_omits_the_series_number() -> None:
    assert "number" not in technote_citation().to_bibtex()


def test_bibtex_url_falls_back_to_the_doi_url() -> None:
    citation = Citation(doi="10.5281/zenodo.10385500", title="Untitled")
    assert citation.to_bibtex() == (
        "@misc{untitled,\n"
        "    title = {{Untitled}},\n"
        "    doi = {10.5281/zenodo.10385500},\n"
        "    url = {https://doi.org/10.5281/zenodo.10385500}\n"
        "}"
    )


def test_bibtex_omits_blank_fields() -> None:
    """A field whose value reduces to nothing once collapsed and escaped is
    absent from the entry, rather than written as an empty pair of braces.
    """
    citation = Citation(
        title="Real Title",
        authors=(PersonAuthor(family_name="   "),),
        publisher="   ",
        number="  ",
        url="  ",
    )
    assert citation.to_bibtex(entry_type=BibtexEntryType.techreport) == (
        "@techreport{real,\n    title = {{Real Title}}\n}"
    )


def test_bibtex_keeps_a_blank_title_field() -> None:
    """The title is BibTeX-required, so an entry composed from a blank title
    still carries an empty title field rather than silently dropping it.
    """
    citation = Citation(title=" ", doi="10.5281/zenodo.10385500")
    assert citation.to_bibtex() == (
        "@misc{citation,\n"
        "    title = {{}},\n"
        "    doi = {10.5281/zenodo.10385500},\n"
        "    url = {https://doi.org/10.5281/zenodo.10385500}\n"
        "}"
    )


def test_bibtex_key_falls_back_when_no_component_survives() -> None:
    """A citation with no author, no date, and a title whose first word is
    entirely non-ASCII has nothing left once its components are slugified,
    so its key falls back to a literal rather than composing an empty one.
    """
    citation = Citation(title="天文学 のデータ")
    assert citation.bibtex_key == "citation"
    assert citation.to_bibtex() == (
        "@misc{citation,\n    title = {{天文学 のデータ}}\n}"
    )


def test_html_context_for_a_person_author() -> None:
    """A person's html_context entry carries both name orders: reading order
    for schema.org and family-name-first for a bibliographic reference.
    """
    citation = GuideCitation(
        citation=Citation(
            doi="10.5281/zenodo.10385500",
            title="Documenteer",
            authors=(
                PersonAuthor(
                    family_name="Sick",
                    given_name="Jonathan",
                    orcid="https://orcid.org/0000-0003-3001-676X",
                    affiliation="Rubin Observatory",
                ),
            ),
            date=PartialDate(2026, 2, 1),
        ),
        label="Software",
        is_self=True,
        in_footer=True,
        note="Cite the software.",
    )

    context = citation.to_html_context()
    assert context["authors"] == [
        {
            "type": "person",
            "name": "Jonathan Sick",
            "citation_name": "Sick, Jonathan",
            "orcid": "https://orcid.org/0000-0003-3001-676X",
            "affiliation": "Rubin Observatory",
        }
    ]
    assert context["label"] == "Software"
    assert context["is_self"] is True
    assert context["in_footer"] is True
    assert context["note"] == "Cite the software."
    assert context["year"] == 2026
    assert context["date"] == "2026-02-01"
    assert context["url"] == "https://doi.org/10.5281/zenodo.10385500"


def test_html_context_for_a_family_only_person_author() -> None:
    """A person with no given name has one spelling rather than two: the
    reading order a schema.org ``Person`` wants is the family name itself.
    """
    context = GuideCitation(
        citation=Citation(
            title="Survey Cadence Optimization",
            authors=(
                PersonAuthor(
                    family_name="Survey Cadence Optimization Committee"
                ),
            ),
        )
    ).to_html_context()

    assert context["authors"] == [
        {
            "type": "person",
            "name": "Survey Cadence Optimization Committee",
            "citation_name": "Survey Cadence Optimization Committee",
            "orcid": None,
            "affiliation": None,
        }
    ]


def test_html_context_without_a_date() -> None:
    """A citation with no date reports neither a date nor a year."""
    context = GuideCitation(
        citation=Citation(doi="10.5281/zenodo.10385500", title="Untitled")
    ).to_html_context()
    assert context["date"] is None
    assert context["year"] is None
    assert context["label"] is None
    assert context["is_self"] is False
    assert context["in_footer"] is False


def test_html_context_splits_the_citation_for_linking() -> None:
    """The context carries the plain-text citation pre-split at its trailing
    location, so a surface can render that location as a hyperlink without
    doing the string surgery itself.
    """
    context = GuideCitation(
        citation=Citation(
            doi="10.5281/zenodo.10385500",
            title="Documenteer",
            authors=(OrganizationAuthor(name="Vera C. Rubin Observatory"),),
            date=PartialDate(2026, 2, 1),
        )
    ).to_html_context()

    assert context["plain_text_url"] == (
        "https://doi.org/10.5281/zenodo.10385500"
    )
    assert context["plain_text_lead"] == (
        "Vera C. Rubin Observatory (2026). Documenteer. "
    )
    # The two halves always reconstitute the citation exactly, which is what
    # lets a surface render them as text plus a link.
    assert (
        context["plain_text_lead"] + context["plain_text_url"]
        == context["plain_text"]
    )


def test_html_context_for_a_citation_without_a_location() -> None:
    """A citation with neither a DOI nor a URL has nothing to link, and its
    lead is the whole citation.
    """
    context = GuideCitation(
        citation=Citation(title="Untitled")
    ).to_html_context()

    assert context["plain_text_url"] is None
    assert context["plain_text_lead"] == context["plain_text"] == "Untitled."


def test_html_context_for_a_citation_with_a_blank_url() -> None:
    """A blank URL is absent everywhere in the mapping, so the surfaces that
    read it cannot disagree about whether the work has a location.
    """
    context = GuideCitation(
        citation=Citation(title="Untitled", url="   ")
    ).to_html_context()

    assert context["url"] is None
    assert context["plain_text_url"] is None
    assert context["plain_text_lead"] == context["plain_text"] == "Untitled."


SITE_URL = "https://guide.lsst.io/"


def _self_citation_context(**overrides: object) -> dict[str, object]:
    """Build a self-citation html_context mapping, as set_citations
    publishes it.
    """
    context = GuideCitation(
        citation=Citation(
            doi="10.71929/rubin/2570308",
            title="Data Preview 2 Documentation",
            authors=(OrganizationAuthor(name="Vera C. Rubin Observatory"),),
            publisher="Vera C. Rubin Observatory",
            date=PartialDate(2025, 6, 30),
        ),
        label="Site",
        is_self=True,
    ).to_html_context()
    context.update(overrides)
    return context


def test_landing_page_jsonld_describes_the_self_citation() -> None:
    """The self citation is the JSON-LD document's own subject: a WebSite
    identified by its DOI.
    """
    payload = json.loads(
        compose_landing_page_jsonld(
            [_self_citation_context()], site_url=SITE_URL
        )
        or ""
    )
    assert payload["@context"] == "https://schema.org"
    assert payload["@type"] == "WebSite"
    assert payload["@id"] == "https://doi.org/10.71929/rubin/2570308"
    assert payload["identifier"] == {
        "@type": "PropertyValue",
        "propertyID": "DOI",
        "value": "10.71929/rubin/2570308",
        "url": "https://doi.org/10.71929/rubin/2570308",
    }
    assert payload["name"] == "Data Preview 2 Documentation"
    assert payload["url"] == SITE_URL
    assert payload["creator"] == [
        {"@type": "Organization", "name": "Vera C. Rubin Observatory"}
    ]
    assert payload["publisher"] == {
        "@type": "Organization",
        "name": "Vera C. Rubin Observatory",
    }
    assert payload["datePublished"] == "2025-06-30"
    assert "citation" not in payload


def _dataset_citation_context() -> dict[str, object]:
    """Build a dataset citation's html_context mapping, credited to both an
    organization and a person so that both author node shapes are exercised.

    The site shows it in the footer, which is what carries it into the
    site-wide JSON-LD block.
    """
    return GuideCitation(
        citation=Citation(
            doi="10.5281/zenodo.10385500",
            title="Images & Catalogs",
            type=CitationType.dataset,
            authors=(
                OrganizationAuthor(
                    name="Vera C. Rubin Observatory",
                    ror="https://ror.org/048g3cy84",
                ),
                PersonAuthor(
                    family_name="Sick",
                    given_name="Jonathan",
                    orcid="0000-0003-3001-676X",
                    affiliation="Rubin Observatory",
                ),
            ),
        ),
        label="Dataset",
        in_footer=True,
    ).to_html_context()


def _product_citation_context(
    *, doi: str, title: str, fragment: str | None = None
) -> dict[str, object]:
    """Build the html_context mapping of a citation whose landing page is a
    page inside the site.
    """
    return GuideCitation(
        citation=Citation(
            doi=doi,
            title=title,
            type=CitationType.dataset,
            authors=(OrganizationAuthor(name="Vera C. Rubin Observatory"),),
        ),
        label=title,
        page="products/object",
        page_fragment=fragment,
    ).to_html_context()


def _paper_citation_context(**overrides: object) -> dict[str, object]:
    """Build the html_context mapping of a paper the site cites in its
    footer.
    """
    context = GuideCitation(
        citation=Citation(
            doi="10.5281/zenodo.10385501",
            title="The Smoke Test Survey",
            type=CitationType.article,
            authors=(PersonAuthor(family_name="Sick", given_name="Jonathan"),),
        ),
        label="Paper",
        in_footer=True,
    ).to_html_context()
    context.update(overrides)
    return context


@pytest.mark.parametrize(
    ("citation_type", "schema_type"),
    [
        (CitationType.dataset, "Dataset"),
        (CitationType.article, "ScholarlyArticle"),
        (CitationType.software, "SoftwareSourceCode"),
        (CitationType.report, "Report"),
        (CitationType.other, "CreativeWork"),
    ],
)
def test_landing_page_jsonld_types_a_citation_from_its_type(
    citation_type: CitationType, schema_type: str
) -> None:
    """A citation's type chooses the schema.org type of its node, so a work
    is typed by what it is rather than by how its label happens to read.
    """
    payload = json.loads(
        compose_landing_page_jsonld(
            [
                GuideCitation(
                    citation=Citation(
                        doi="10.5281/zenodo.10385500",
                        title="Object catalog",
                        type=citation_type,
                    ),
                    label="Object catalog",
                    in_footer=True,
                ).to_html_context()
            ]
        )
        or ""
    )

    (node,) = payload["citation"]
    assert node["@type"] == schema_type


def test_landing_page_jsonld_types_a_dataset() -> None:
    """A citation typed as a dataset is a schema.org Dataset hanging off the
    self citation, and its authors carry resolvable ORCID and ROR ids.
    """
    payload = json.loads(
        compose_landing_page_jsonld(
            [_self_citation_context(), _dataset_citation_context()],
            site_url=SITE_URL,
        )
        or ""
    )
    (dataset,) = payload["citation"]
    assert dataset["@type"] == "Dataset"
    assert dataset["@id"] == "https://doi.org/10.5281/zenodo.10385500"
    assert dataset["name"] == "Images & Catalogs"
    assert dataset["creator"] == [
        {
            "@type": "Organization",
            "@id": "https://ror.org/048g3cy84",
            "name": "Vera C. Rubin Observatory",
        },
        {
            "@type": "Person",
            "@id": "https://orcid.org/0000-0003-3001-676X",
            "name": "Jonathan Sick",
            "affiliation": {
                "@type": "Organization",
                "name": "Rubin Observatory",
            },
        },
    ]
    # A cited work that is not the site keeps its own landing page, not the
    # site's URL.
    assert dataset["url"] == "https://doi.org/10.5281/zenodo.10385500"


def test_landing_page_jsonld_relates_parts_and_cited_works() -> None:
    """The site-wide block states a *relation* for each entry it carries: an
    entry that claims a page is a part of the site's own work, an entry the
    footer shows is a work the site cites, and an entry that is neither is
    left out of the block entirely.
    """
    payload = json.loads(
        compose_landing_page_jsonld(
            [
                _self_citation_context(),
                _paper_citation_context(),
                _product_citation_context(
                    doi="10.71929/rubin/3382539",
                    title="Object catalog (Butler)",
                ),
                _product_citation_context(
                    doi="10.71929/rubin/3382540",
                    title="Object catalog (TAP)",
                ),
                # Neither a part nor in the footer, so the site-wide block
                # says nothing about it.
                GuideCitation(
                    citation=Citation(
                        doi="10.5281/zenodo.10385500",
                        title="Images & Catalogs",
                        type=CitationType.dataset,
                    ),
                    label="Unlisted",
                ).to_html_context(),
            ],
            site_url=SITE_URL,
        )
        or ""
    )

    assert payload["@id"] == "https://doi.org/10.71929/rubin/2570308"

    # The parts are named by reference alone -- type, identifier, and name --
    # because each one's own landing page carries the full record.
    assert payload["hasPart"] == [
        {
            "@type": "Dataset",
            "@id": "https://doi.org/10.71929/rubin/3382539",
            "name": "Object catalog (Butler)",
        },
        {
            "@type": "Dataset",
            "@id": "https://doi.org/10.71929/rubin/3382540",
            "name": "Object catalog (TAP)",
        },
    ]

    # The cited work is the one the site displays, and it appears in full
    # because no other page of the site describes it.
    (paper,) = payload["citation"]
    assert paper["@type"] == "ScholarlyArticle"
    assert paper["name"] == "The Smoke Test Survey"
    assert paper["creator"] == [{"@type": "Person", "name": "Jonathan Sick"}]

    assert "10.5281/zenodo.10385500" not in json.dumps(payload)


def test_landing_page_jsonld_states_no_relation_it_does_not_have() -> None:
    """A site whose only citation is its own states neither relation: an
    empty ``hasPart`` or ``citation`` would claim the site has parts, or
    cites works, when it does neither.
    """
    payload = json.loads(
        compose_landing_page_jsonld(
            [_self_citation_context()], site_url=SITE_URL
        )
        or ""
    )

    assert "hasPart" not in payload
    assert "citation" not in payload


def test_landing_page_jsonld_site_subject_makes_the_same_selection() -> None:
    """A site without a self citation relates its entries to the site subject
    exactly as one with a self citation relates them to its own work: the
    same entries, under the same relations, in the same shapes.
    """
    payload = json.loads(
        compose_landing_page_jsonld(
            [
                _paper_citation_context(),
                _product_citation_context(
                    doi="10.71929/rubin/3382539",
                    title="Object catalog (Butler)",
                ),
                GuideCitation(
                    citation=Citation(
                        doi="10.5281/zenodo.10385500",
                        title="Images & Catalogs",
                    ),
                    label="Unlisted",
                ).to_html_context(),
            ]
        )
        or ""
    )

    # A part is named by reference alone here too: its full record lives on
    # the page it claims, whether or not the site declares a work of its own.
    assert payload["hasPart"] == [
        {
            "@type": "Dataset",
            "@id": "https://doi.org/10.71929/rubin/3382539",
            "name": "Object catalog (Butler)",
        }
    ]
    (paper,) = payload["citation"]
    assert paper["name"] == "The Smoke Test Survey"
    assert paper["creator"] == [{"@type": "Person", "name": "Jonathan Sick"}]
    # The unlisted entry is neither a part nor shown in the footer, so it is
    # absent from the block, exactly as it is with a self citation.
    assert "10.5281/zenodo.10385500" not in json.dumps(payload)


def test_landing_page_jsonld_without_a_selected_citation() -> None:
    """A site whose citations are all displayed on cards alone has nothing to
    say site-wide, so it emits no block rather than an empty one.
    """
    assert (
        compose_landing_page_jsonld(
            [
                GuideCitation(
                    citation=Citation(
                        doi="10.5281/zenodo.10385500",
                        title="Images & Catalogs",
                    ),
                    label="Unlisted",
                ).to_html_context()
            ]
        )
        is None
    )


def test_landing_page_jsonld_describes_the_site_without_a_self_citation() -> (
    None
):
    """A site that claims no DOI's landing page is still a site, so the
    document's subject is the site itself — a WebSite with no identifier —
    and the works it declares hang off it as citations.
    """
    payload = json.loads(
        compose_landing_page_jsonld(
            [_dataset_citation_context()],
            site_url=SITE_URL,
            site_title="Butler Guide",
        )
        or ""
    )
    assert payload["@context"] == "https://schema.org"
    assert payload["@type"] == "WebSite"
    assert payload["name"] == "Butler Guide"
    assert payload["url"] == SITE_URL
    # The site claims no DOI of its own, so the subject carries neither an
    # identifier nor an @id that would assert one.
    assert "@id" not in payload
    assert "identifier" not in payload
    assert "@graph" not in payload
    (node,) = payload["citation"]
    assert node["@type"] == "Dataset"
    assert node["@id"] == "https://doi.org/10.5281/zenodo.10385500"


def test_landing_page_jsonld_site_subject_without_a_url_or_title() -> None:
    """A site that declares no base_url states no url rather than an empty
    one, and the same for its title, so the subject asserts only what the
    configuration knows.
    """
    payload = json.loads(
        compose_landing_page_jsonld([_dataset_citation_context()]) or ""
    )

    assert payload["@type"] == "WebSite"
    assert "url" not in payload
    assert "name" not in payload


def test_landing_page_jsonld_ignores_a_label_that_reads_as_a_type() -> None:
    """A label is a display string and carries no schema semantics, so an
    untyped citation labelled "Dataset" is still a generic CreativeWork.
    """
    payload = json.loads(
        compose_landing_page_jsonld(
            [
                _self_citation_context(),
                GuideCitation(
                    citation=Citation(
                        doi="10.5281/zenodo.10385500",
                        title="Images & Catalogs",
                    ),
                    label="Dataset",
                    in_footer=True,
                ).to_html_context(),
            ]
        )
        or ""
    )

    (node,) = payload["citation"]
    assert node["@type"] == "CreativeWork"


def test_landing_page_jsonld_types_a_self_citation() -> None:
    """A self citation that declares a type is published under it, so a site
    that is a data release's landing page is a Dataset rather than a WebSite.
    """
    payload = json.loads(
        compose_landing_page_jsonld(
            [_self_citation_context(type="dataset")], site_url=SITE_URL
        )
        or ""
    )

    assert payload["@type"] == "Dataset"
    # It is still the document's own subject, described by the site's URL.
    assert payload["url"] == SITE_URL


def test_landing_page_jsonld_without_citations() -> None:
    """A site that declares no citations emits no JSON-LD block at all."""
    assert compose_landing_page_jsonld([]) is None


def test_landing_page_jsonld_cannot_break_out_of_a_script_element() -> None:
    """A title carrying markup, quotes, or an ampersand is escaped so that it
    cannot close the <script> element the block is embedded in.
    """
    serialized = compose_landing_page_jsonld(
        [
            _self_citation_context(
                title='</script><img src=x onerror="alert(1)"> & "quoted"'
            )
        ]
    )
    assert serialized is not None
    assert "<" not in serialized
    assert ">" not in serialized
    assert "&" not in serialized
    # The escaping is JSON's own, so the title survives a round trip intact.
    assert (
        json.loads(serialized)["name"]
        == '</script><img src=x onerror="alert(1)"> & "quoted"'
    )


PAGE_URL = "https://guide.lsst.io/products/object.html"


def test_page_jsonld_describes_a_single_claiming_citation() -> None:
    """A page a single citation claims is that citation's landing page, so
    the citation is the document's own subject and its url is the page's own,
    fragment included, rather than the doi.org redirect.
    """
    payload = json.loads(
        compose_page_jsonld(
            [
                _product_citation_context(
                    doi="10.71929/rubin/3382540",
                    title="Object catalog (TAP)",
                    fragment="tap",
                )
            ],
            page_url=PAGE_URL,
        )
        or ""
    )

    assert payload["@context"] == "https://schema.org"
    assert payload["@type"] == "Dataset"
    assert payload["@id"] == "https://doi.org/10.71929/rubin/3382540"
    assert payload["name"] == "Object catalog (TAP)"
    assert payload["url"] == f"{PAGE_URL}#tap"
    assert "@graph" not in payload


def test_page_jsonld_states_the_part_relation() -> None:
    """A page's own work is a part of the site's, so its node points back at
    the site's citation — by reference alone, because the site's own pages
    carry that record in full.
    """
    payload = json.loads(
        compose_page_jsonld(
            [
                _product_citation_context(
                    doi="10.71929/rubin/3382540",
                    title="Object catalog (TAP)",
                    fragment="tap",
                )
            ],
            page_url=PAGE_URL,
            self_citation=_self_citation_context(),
        )
        or ""
    )

    assert payload["isPartOf"] == {
        "@type": "WebSite",
        "@id": "https://doi.org/10.71929/rubin/2570308",
        "name": "Data Preview 2 Documentation",
    }


def test_page_jsonld_graphs_several_claiming_citations() -> None:
    """Two citations whose landing page is the same page are both the
    document's subject, so neither is subordinated to the other: they are
    emitted as a @graph, each keeping its own fragment.
    """
    payload = json.loads(
        compose_page_jsonld(
            [
                _product_citation_context(
                    doi="10.71929/rubin/3382539",
                    title="Object catalog (Butler)",
                    fragment="butler",
                ),
                _product_citation_context(
                    doi="10.71929/rubin/3382540",
                    title="Object catalog (TAP)",
                    fragment="tap",
                ),
            ],
            page_url=PAGE_URL,
        )
        or ""
    )

    assert payload["@context"] == "https://schema.org"
    butler, tap = payload["@graph"]
    assert butler["url"] == f"{PAGE_URL}#butler"
    assert tap["url"] == f"{PAGE_URL}#tap"


def test_page_jsonld_without_a_fragment_is_the_page_itself() -> None:
    """A claim that names no fragment describes the whole page."""
    payload = json.loads(
        compose_page_jsonld(
            [
                _product_citation_context(
                    doi="10.71929/rubin/3382539",
                    title="Object catalog",
                    fragment=None,
                )
            ],
            page_url=PAGE_URL,
        )
        or ""
    )

    assert payload["url"] == PAGE_URL


def test_page_jsonld_falls_back_to_the_doi_url() -> None:
    """A site that declares no base_url cannot know the page's own URL, so
    the node keeps the doi.org redirect it would carry anywhere else.
    """
    payload = json.loads(
        compose_page_jsonld(
            [
                _product_citation_context(
                    doi="10.71929/rubin/3382540",
                    title="Object catalog (TAP)",
                    fragment="tap",
                )
            ]
        )
        or ""
    )

    assert payload["url"] == "https://doi.org/10.71929/rubin/3382540"


def test_page_jsonld_without_citations() -> None:
    """A page no citation claims gets no block of its own."""
    assert compose_page_jsonld([], page_url=PAGE_URL) is None


def test_page_jsonld_cannot_break_out_of_a_script_element() -> None:
    """The page block is escaped exactly as the site-wide one is."""
    serialized = compose_page_jsonld(
        [
            _product_citation_context(
                doi="10.71929/rubin/3382540",
                title="Object catalog </script>& more",
                fragment="tap",
            )
        ],
        page_url=PAGE_URL,
    )
    assert serialized is not None
    assert "<" not in serialized
    assert ">" not in serialized
    assert "&" not in serialized
    assert json.loads(serialized)["name"] == "Object catalog </script>& more"


@pytest.mark.parametrize(
    "value",
    [
        "0000-0003-3001-676x",
        "0000-0003-3001-676X",
        "https://orcid.org/0000-0003-3001-676X",
        "http://orcid.org/0000-0003-3001-676X/",
    ],
)
def test_orcid_url_accepts_spellings(value: str) -> None:
    assert orcid_url(value) == "https://orcid.org/0000-0003-3001-676X"


@pytest.mark.parametrize(
    "value", ["048g3cy84", "https://ror.org/048g3cy84", "ror.org/048g3cy84/"]
)
def test_ror_url_accepts_spellings(value: str) -> None:
    assert ror_url(value) == "https://ror.org/048g3cy84"


def test_partial_date_states_the_precision_it_was_given() -> None:
    """A publication date isoformats at the precision its source stated,
    rather than being padded out to a day nobody wrote down.
    """
    assert PartialDate(2025).isoformat() == "2025"
    assert PartialDate(2025, 6).isoformat() == "2025-06"
    assert PartialDate(2025, 6, 30).isoformat() == "2025-06-30"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2025", PartialDate(2025)),
        ("2025-06", PartialDate(2025, 6)),
        ("2025-06-30", PartialDate(2025, 6, 30)),
        (" 2025-06 ", PartialDate(2025, 6)),
    ],
)
def test_partial_date_parses_each_iso_precision(
    text: str, expected: PartialDate
) -> None:
    """Each of ISO 8601's three date precisions reads back at that
    precision.
    """
    assert PartialDate.parse(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "June 2025",
        "2025-13",
        "2025-6",
        "25-06",
        "2025-06-31",
        "2025-02-30",
        "2025-06-00",
        "2025-06-30-01",
        "2025/06/30",
        "",
        "-2025",
        # Arabic-Indic digits, which int() reads but ISO 8601 does not write.
        "٢٠٢٥-٠٦-٣٠",
    ],
)
def test_partial_date_rejects_text_that_is_not_a_date(text: str) -> None:
    """Text that is not one of the three ISO 8601 forms, or that states a
    month or a day outside its range, is rejected rather than guessed at.
    """
    with pytest.raises(ValueError, match="date"):
        PartialDate.parse(text)


def test_partial_date_rejects_a_year_that_is_not_four_digits() -> None:
    """A year outside four digits is a typo, not a publication year."""
    with pytest.raises(ValueError, match="four digits"):
        PartialDate(20250)


def test_partial_date_rejects_a_day_without_a_month() -> None:
    """A day is only meaningful within a month, so stating one without the
    other is an error rather than a date with a hole in it.
    """
    with pytest.raises(ValueError, match="without a month"):
        PartialDate(2025, day=30)


def test_partial_date_rejects_a_day_of_zero() -> None:
    """A zero day is a day no calendar has, so it is range-checked as
    written rather than as a first-of-the-month substituted for it.
    """
    with pytest.raises(ValueError, match="Not a date"):
        PartialDate(2025, 6, 0)


def test_partial_date_round_trips_a_calendar_date() -> None:
    """A full calendar date survives the trip through the partial date and
    back, and a reduced-precision date has no day to return.
    """
    full = PartialDate.from_date(datetime.date(2025, 6, 30))
    assert full == PartialDate(2025, 6, 30)
    assert full.to_date() == datetime.date(2025, 6, 30)
    assert PartialDate(2025, 6).to_date() is None
    assert PartialDate(2025).to_date() is None


def test_partial_date_is_its_iso_form_as_text() -> None:
    """A partial date renders as its ISO form wherever text is wanted, so a
    template or an f-string never has to reach for ``isoformat``.
    """
    assert f"{PartialDate(2025, 6)}" == "2025-06"
