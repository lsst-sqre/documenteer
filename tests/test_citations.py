"""Tests for the documenteer.citations module."""

from __future__ import annotations

import datetime
import json

import pytest

from documenteer.citations import (
    BibtexEntryType,
    Citation,
    GuideCitation,
    OrganizationAuthor,
    PersonAuthor,
    compose_landing_page_jsonld,
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
        "DOI:10.5281/zenodo.10385500",
        "https://doi.org/10.5281/zenodo.10385500",
        "http://doi.org/10.5281/zenodo.10385500",
        "https://dx.doi.org/10.5281/zenodo.10385500",
        "  10.5281/zenodo.10385500  ",
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
        date=datetime.date(2025, 6, 30),
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


def dataset_citation() -> Citation:
    """Build a dataset citation credited to an organization."""
    return Citation(
        doi="10.71929/rubin/2570308",
        title="Data Preview 2",
        authors=(OrganizationAuthor(name="Vera C. Rubin Observatory"),),
        publisher="Vera C. Rubin Observatory",
        date=datetime.date(2025, 6, 30),
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
        date=datetime.date(2026, 8, 24),
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
            date=datetime.date(2026, 2, 1),
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
            date=datetime.date(2026, 2, 1),
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
            date=datetime.date(2025, 6, 30),
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
    """
    return GuideCitation(
        citation=Citation(
            doi="10.5281/zenodo.10385500",
            title="Images & Catalogs",
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
    ).to_html_context()


def test_landing_page_jsonld_types_a_dataset_label() -> None:
    """A citation labelled "Dataset" is a schema.org Dataset hanging off the
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


def test_landing_page_jsonld_is_a_graph_without_a_self_citation() -> None:
    """A site that marks no citation as its own has no subject to make the
    document about, so its citations are emitted as a plain @graph.
    """
    payload = json.loads(
        compose_landing_page_jsonld([_dataset_citation_context()]) or ""
    )
    assert payload["@context"] == "https://schema.org"
    assert "@id" not in payload
    (node,) = payload["@graph"]
    assert node["@type"] == "Dataset"


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
