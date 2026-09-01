"""Tests for documenteer.ext.bibtex."""

from __future__ import annotations

import pytest
from pybtex.database import BibliographyData, parse_string

from documenteer.ext.bibtex import LsstBibtexStyle

BIB = r"""
@software{2011ascl.soft08003C,
       author = {{Calabretta}, M.~R.},
        title = "{Wcslib and Pgsbox}",
 howpublished = {Astrophysics Source Code Library, record ascl:1108.003},
         year = 2011,
        month = aug,
          eid = {ascl:1108.003},
archivePrefix = {ascl},
       eprint = {1108.003},
       adsurl = {https://ui.adsabs.harvard.edu/abs/2011ascl.soft08003C},
      adsnote = {Provided by the SAO/NASA Astrophysics Data System}
}

@misc{ascl-as-misc,
        title = "{Some Other Code}",
         year = 2011,
archivePrefix = {ascl},
       eprint = {1108.004}
}

@inproceedings{2005ASPC..347..119G,
       author = {{Greisen}, Eric W.},
        title = "{Some ADASS Paper}",
    booktitle = {Astronomical Data Analysis Software and Systems XIV},
         year = 2005,
       series = {Astronomical Society of the Pacific Conference Series},
       volume = {347},
        month = dec,
        pages = {119},
       adsurl = {https://ui.adsabs.harvard.edu/abs/2005ASPC..347..119G},
      adsnote = {Provided by the SAO/NASA Astrophysics Data System}
}

@article{2002A&A...395.1077C,
       author = {{Calabretta}, M.~R. and {Greisen}, E.~W.},
        title = "{Representations of celestial coordinates in FITS}",
      journal = {\aap},
         year = 2002,
        month = dec,
       volume = {395},
        pages = {1077-1122},
          doi = {10.1051/0004-6361:20021327},
archivePrefix = {arXiv},
       eprint = {astro-ph/0207413},
 primaryClass = {astro-ph},
       adsurl = {https://ui.adsabs.harvard.edu/abs/2002A&A...395.1077C},
      adsnote = {Provided by the SAO/NASA Astrophysics Data System}
}

@article{no-ads,
       author = {{Doe}, J.},
        title = "{No ADS record here}",
      journal = {\apj},
         year = 2020,
          doi = {10.1234/nothing}
}

@misc{escaped-adsurl,
       author = {{Astropy Collaboration}},
        title = "{Astropy}",
         year = 2013,
       adsurl = {http://adsabs.harvard.edu/abs/2013A\%26A...558A..33A}
}

@misc{note-ends-in-abbreviation,
       author = {{Author}, A.},
        title = "{A title}",
         year = 2020,
         note = {See discussion by Smith et al.},
       adsurl = {https://ui.adsabs.harvard.edu/abs/2020abbr}
}

@misc{note-ends-in-question-mark,
       author = {{Author}, A.},
        title = "{Is this a question}",
         year = 2020,
         note = {Really?},
       adsurl = {https://ui.adsabs.harvard.edu/abs/2020question}
}
"""


@pytest.fixture
def bib_data() -> BibliographyData:
    return parse_string(BIB, "bibtex")


def render(bib_data: BibliographyData) -> dict[str, str]:
    """Format every entry with the Rubin style, as plain text."""
    style = LsstBibtexStyle()
    return {
        entry.key: entry.text.render_as("text")
        for entry in style.format_entries(bib_data.entries.values())
    }


def test_formatting_is_idempotent(bib_data: BibliographyData) -> None:
    """Formatting must not mutate the entries.

    Sphinx formats each entry more than once; a style that rewrites entry
    fields in place renders differently on subsequent passes.
    """
    assert render(bib_data) == render(bib_data)


def test_ascl_software(bib_data: BibliographyData) -> None:
    """An ASCL record links to ascl.net, never to arXiv."""
    text = render(bib_data)["2011ascl.soft08003C"]
    assert "ascl:1108.003" in text
    assert "arXiv" not in text
    assert text.endswith("ascl:1108.003 [ADS].")


def test_ascl_archive_prefix_without_eid(bib_data: BibliographyData) -> None:
    """An ``archivePrefix`` of ascl is honored for any entry type."""
    text = render(bib_data)["ascl-as-misc"]
    assert "ascl:1108.004" in text
    assert "arXiv" not in text


def test_ads_link_without_other_links(bib_data: BibliographyData) -> None:
    """A conference paper with no DOI still gets an ADS link.

    With no other links to join, the marker stands as its own sentence, just
    as a lone DOI would.
    """
    text = render(bib_data)["2005ASPC..347..119G"]
    assert text.endswith("December 2005. [ADS].")


def test_ads_link_follows_other_links(bib_data: BibliographyData) -> None:
    """The ADS link comes last, with no comma before the bracket."""
    text = render(bib_data)["2002A&A...395.1077C"]
    assert text.endswith(
        "arXiv:astro-ph/0207413, doi:10.1051/0004-6361:20021327 [ADS]."
    )


def test_no_ads_url(bib_data: BibliographyData) -> None:
    """Entries without an adsurl field are unaffected."""
    text = render(bib_data)["no-ads"]
    assert "[ADS]" not in text
    assert text.endswith("doi:10.1234/nothing.")


def test_ascl_url_is_linked(bib_data: BibliographyData) -> None:
    """The ASCL and ADS identifiers are rendered as hyperlinks."""
    style = LsstBibtexStyle()
    entries = {
        entry.key: entry.text.render_as("html")
        for entry in style.format_entries(bib_data.entries.values())
    }
    html = entries["2011ascl.soft08003C"]
    assert 'href="https://ascl.net/1108.003"' in html
    assert (
        'href="https://ui.adsabs.harvard.edu/abs/2011ascl.soft08003C"' in html
    )


def test_ads_link_does_not_disturb_the_note(
    bib_data: BibliographyData,
) -> None:
    """The ADS link is appended without editing the rendered sentence.

    A note ending in an abbreviation shares its period with the sentence
    terminator, and a note ending in another terminator keeps it.
    """
    text = render(bib_data)
    assert text["note-ends-in-abbreviation"].endswith(
        "See discussion by Smith et al. [ADS]."
    )
    assert text["note-ends-in-question-mark"].endswith("Really? [ADS].")


def test_latex_escaping_is_stripped_from_ads_url(
    bib_data: BibliographyData,
) -> None:
    """ADS exports escape ``&`` and ``%`` for LaTeX; links must not.

    A literal backslash in the href makes the link a 404.
    """
    style = LsstBibtexStyle()
    entries = {
        entry.key: entry.text.render_as("html")
        for entry in style.format_entries(bib_data.entries.values())
    }
    html = entries["escaped-adsurl"]
    assert 'href="http://adsabs.harvard.edu/abs/2013A%26A...558A..33A"' in html
    assert "\\" not in html
