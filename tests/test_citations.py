"""Tests for the documenteer.citations module."""

from __future__ import annotations

import datetime

import pytest

from documenteer.citations import (
    BibtexEntryType,
    Citation,
    OrganizationAuthor,
    PersonAuthor,
    doi_url,
    normalize_doi,
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
