"""Test the documenteer.toml configuration support."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from sphinx.errors import ConfigError

from documenteer.citations import (
    CitationType,
    OrganizationAuthor,
    PartialDate,
    PersonAuthor,
)
from documenteer.conf import DocumenteerConfig

EXAMPLE = """

[project]
title = "Documenteer"
base_url = "https://documenteer.lsst.io"
copyright = "2022 AURA"
github_url = "https://github.com/lsst-sqre/documenteer"
version = "1.0.0"

[sphinx]
extensions = [
    "sphinx_design",
    "new_extension",
]
nitpick_ignore = [
    ["py:class", "pydantic.main.BaseModel"]
]
nitpick_ignore_regex = [
    ["py:.+", 'fastapi\\..+']
]

[sphinx.intersphinx.projects]
sphinx = "https://www.sphinx-doc.org/en/master/"
documenteer = "https://documenteer.lsst.io"
python = "https://docs.python.org/3/"

[sphinx.linkcheck]
ignore = [
    "^https://confluence.lsstcorp.org/"
]
"""

EXAMPLE_BAD_PACKAGE = """
[project]
title = "Documenteer"
base_url = "https://documenteer.lsst.io"
copyright = "2022 AURA"
github_url = "https://github.com/lsst-sqre/documenteer"

[project.python]
package = "notapackage"
"""

EXAMPLE_PYTHON = """

[project]
title = "Documenteer"
copyright = "2022 AURA"

[project.python]
package = "documenteer"
"""

EXAMPLE_SIDEBARS = """

[project]
title = "Documenteer"
copyright = "2022 AURA"

[project.python]
package = "documenteer"

[sphinx]
disable_primary_sidebars = [
    "index",
    "changelog",
]
"""

EXAMPLE_NO_LAST_UPDATED = """

[project]
title = "Documenteer"
copyright = "2022 AURA"

[sphinx.theme]
show_last_updated = false
"""

EXAMPLE_NO_SPHINX = """

[project]
title = "Documenteer"
copyright = "2022 AURA"
"""

EXAMPLE_NO_GITHUB_EDIT_LINK = """

[project]
title = "Documenteer"
copyright = "2022 AURA"
github_url = "https://github.com/lsst-sqre/documenteer"

[sphinx.theme]
show_github_edit_link = false
"""


def test_load() -> None:
    config = DocumenteerConfig.load(EXAMPLE)
    assert config.project == "Documenteer"
    assert config.base_url == "https://documenteer.lsst.io/"
    assert config.copyright == "2022 AURA"
    assert config.github_url == "https://github.com/lsst-sqre/documenteer"
    assert config.version == "1.0.0"
    assert config.automodapi_toctreedirm == "api"


def test_bad_package() -> None:
    with pytest.raises(ConfigError):
        DocumenteerConfig.load(EXAMPLE_BAD_PACKAGE)


def test_python_metadata() -> None:
    config = DocumenteerConfig.load(EXAMPLE_PYTHON)
    assert config.project == "Documenteer"
    assert config.base_url == "https://documenteer.lsst.io"
    assert config.copyright == "2022 AURA"
    assert config.github_url == "https://github.com/lsst-sqre/documenteer"
    assert isinstance(config.version, str)


def test_append_extensions() -> None:
    """Test DocumenteerConfig.append_extensions()."""
    config = DocumenteerConfig.load(EXAMPLE)

    existing_extensions = [
        "sphinx_design",
        "sphinx.ext.autodoc",
        "documenteer.ext.jira",
    ]
    config.append_extensions(existing_extensions)
    assert existing_extensions == [
        "sphinx_design",
        "sphinx.ext.autodoc",
        "documenteer.ext.jira",
        "new_extension",
    ]


def test_append_intersphinx_projects() -> None:
    config = DocumenteerConfig.load(EXAMPLE)

    projects: dict[str, tuple[str, str | None]] = {
        "python": ("https://docs.python.org/3/", None),
    }
    config.extend_intersphinx_mapping(projects)
    assert projects == {
        "python": ("https://docs.python.org/3/", None),
        "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
        "documenteer": ("https://documenteer.lsst.io/", None),
    }


def test_append_linkcheck_ignore() -> None:
    config = DocumenteerConfig.load(EXAMPLE)

    linkcheck_ignore = [
        r"^https://rubinobs.atlassian.net/browse/",
        r"^https://ls.st/",
    ]
    config.append_linkcheck_ignore(linkcheck_ignore)
    assert linkcheck_ignore == [
        r"^https://rubinobs.atlassian.net/browse/",
        r"^https://ls.st/",
        r"^https://confluence.lsstcorp.org/",
    ]


def test_disable_primary_sidebars_defaults() -> None:
    """Test sphinx.disable_primary_sidebars defaults where it wasn't set."""
    config = DocumenteerConfig.load(EXAMPLE)
    html_sidebars: dict[str, list[str]] = {}
    config.disable_primary_sidebars(html_sidebars)
    assert html_sidebars == {"index": []}


def test_disable_primary_sidebars() -> None:
    """Test sphinx.disable_primary_sidebars."""
    config = DocumenteerConfig.load(EXAMPLE_SIDEBARS)
    html_sidebars: dict[str, list[str]] = {}
    config.disable_primary_sidebars(html_sidebars)
    assert html_sidebars == {"index": [], "changelog": []}


def test_show_last_updated_default() -> None:
    """show_last_updated defaults to True when not configured."""
    assert DocumenteerConfig.load(EXAMPLE).show_last_updated is True
    # Also defaults to True when there's no [sphinx] table at all.
    assert DocumenteerConfig.load(EXAMPLE_NO_SPHINX).show_last_updated is True


def test_show_last_updated_disabled() -> None:
    """show_last_updated reflects sphinx.theme.show_last_updated = false."""
    config = DocumenteerConfig.load(EXAMPLE_NO_LAST_UPDATED)
    assert config.show_last_updated is False


def test_set_edit_on_github() -> None:
    """The GitHub repository context is set, but not doc_path.

    ``doc_path`` is resolved from the Sphinx source directory by
    ``documenteer.ext.githubeditlink``, which can't run this early.
    """
    config = DocumenteerConfig.load(EXAMPLE)
    html_theme_options: dict = {}
    html_context: dict = {}
    config.set_edit_on_github(html_theme_options, html_context)

    assert html_theme_options["use_edit_page_button"] is True
    assert html_context["github_user"] == "lsst-sqre"
    assert html_context["github_repo"] == "documenteer"
    assert html_context["github_version"] == "main"
    assert "doc_path" not in html_context


def test_set_edit_on_github_disabled() -> None:
    """show_github_edit_link = false leaves the Sphinx settings untouched."""
    config = DocumenteerConfig.load(EXAMPLE_NO_GITHUB_EDIT_LINK)
    html_theme_options: dict = {}
    html_context: dict = {}
    config.set_edit_on_github(html_theme_options, html_context)

    assert html_theme_options == {}
    assert html_context == {}


def test_set_edit_on_github_without_github_url() -> None:
    """The edit link needs project.github_url to build a URL from."""
    config = DocumenteerConfig.load(EXAMPLE_NO_SPHINX)
    with pytest.raises(ConfigError, match=r"project\.github_url is not set"):
        config.set_edit_on_github({}, {})


EXAMPLE_LINKCHECK_SERVICE = """

[project]
title = "Documenteer"
base_url = "https://documenteer.lsst.io"

[sphinx.linkcheck]
use_service = false
service_url = "https://roundtable-dev.lsst.cloud/ook"
poll_budget = 60
strict = true
recheck_unverified = false
origin_base_url = "https://Custom.LSST.io/guides/"
"""


def test_linkcheck_service_defaults() -> None:
    """The link-check service settings have production-ready defaults,
    even without a [sphinx] table.
    """
    for example in (EXAMPLE, EXAMPLE_NO_SPHINX):
        config = DocumenteerConfig.load(example)
        assert config.linkcheck_use_service is True
        assert (
            config.linkcheck_service_url == "https://roundtable.lsst.cloud/ook"
        )
        assert config.linkcheck_poll_budget == 300
        assert config.linkcheck_strict is False
        assert config.linkcheck_recheck_unverified is True


def test_linkcheck_service_settings() -> None:
    """[sphinx.linkcheck] settings override the service defaults."""
    config = DocumenteerConfig.load(EXAMPLE_LINKCHECK_SERVICE)
    assert config.linkcheck_use_service is False
    assert (
        config.linkcheck_service_url == "https://roundtable-dev.lsst.cloud/ook"
    )
    assert config.linkcheck_poll_budget == 60
    assert config.linkcheck_strict is True
    assert config.linkcheck_recheck_unverified is False


def test_linkcheck_origin_derived_from_base_url() -> None:
    """The origin base URL is derived from project.base_url, normalized
    without a trailing slash.
    """
    config = DocumenteerConfig.load(EXAMPLE)
    assert config.linkcheck_origin_base_url == "https://documenteer.lsst.io"


def test_linkcheck_origin_override() -> None:
    """[sphinx.linkcheck] origin_base_url overrides the derived origin
    and is normalized (lowercased host, trailing slash stripped).
    """
    config = DocumenteerConfig.load(EXAMPLE_LINKCHECK_SERVICE)
    assert config.linkcheck_origin_base_url == "https://custom.lsst.io/guides"


def test_linkcheck_origin_no_base_url() -> None:
    """Without a base URL or override, the origin base URL is None."""
    config = DocumenteerConfig.load(EXAMPLE_NO_SPHINX)
    assert config.linkcheck_origin_base_url is None


EXAMPLE_INTERSPHINX_CACHE = """

[project]
title = "Documenteer"
base_url = "https://documenteer.lsst.io"

[sphinx.intersphinx.cache]
use_service = false
service_url = "https://roundtable-dev.lsst.cloud/ook"
disk_cache_ttl = 0
warn_on_permanent_redirect = true
"""

EXAMPLE_INTERSPHINX_CACHE_EMPTY = """

[project]
title = "Documenteer"
base_url = "https://documenteer.lsst.io"

[sphinx.intersphinx.cache]
"""


def test_intersphinx_cache_defaults() -> None:
    """The intersphinx cache settings have production-ready defaults, even
    without a [sphinx] table, and with the table present but empty.
    """
    examples = (EXAMPLE, EXAMPLE_NO_SPHINX, EXAMPLE_INTERSPHINX_CACHE_EMPTY)
    for example in examples:
        config = DocumenteerConfig.load(example)
        assert config.intersphinx_cache_use_service is True
        assert (
            config.intersphinx_cache_service_url
            == "https://roundtable.lsst.cloud/ook"
        )
        assert config.intersphinx_cache_disk_cache_ttl == 600
        # Escalating the permanent-redirect notice to a warning is opt-in:
        # Rubin builds run with -W, and the move is not the author's doing.
        assert config.intersphinx_cache_warn_on_permanent_redirect is False


def test_intersphinx_cache_settings() -> None:
    """[sphinx.intersphinx.cache] settings override the defaults."""
    config = DocumenteerConfig.load(EXAMPLE_INTERSPHINX_CACHE)
    assert config.intersphinx_cache_use_service is False
    assert (
        config.intersphinx_cache_service_url
        == "https://roundtable-dev.lsst.cloud/ook"
    )
    assert config.intersphinx_cache_disk_cache_ttl == 0
    assert config.intersphinx_cache_warn_on_permanent_redirect is True


EXAMPLE_NEGATIVE_TTL = """

[project]
title = "Documenteer"
base_url = "https://documenteer.lsst.io"

[sphinx.intersphinx.cache]
disk_cache_ttl = -1
"""


def test_intersphinx_cache_negative_ttl_rejected() -> None:
    """A negative disk_cache_ttl is rejected at config load rather than
    silently coerced to the fast-path-disabled behavior of 0.
    """
    with pytest.raises(ConfigError):
        DocumenteerConfig.load(EXAMPLE_NEGATIVE_TTL)


EXAMPLE_CITATIONS_INLINE = """

[project]
title = "Data Preview 2 Documentation"
base_url = "https://dp0-2.lsst.io"
github_url = "https://github.com/lsst-sqre/documenteer"

[[project.citations]]
doi = "https://doi.org/10.71929/rubin/2570308"
label = "Dataset"
type = "dataset"
self = true
note = "Cite the DP2 dataset and this documentation."
title = "Data Preview 2"
publisher = "Vera C. Rubin Observatory"
date = 2025-06-30
authors = [
    { name = "Vera C. Rubin Observatory", ror = "https://ror.org/048g3cy84" },
]
"""


def test_citations_inline() -> None:
    """A [[project.citations]] entry composes a citation from its own
    fields, normalizing the DOI.
    """
    config = DocumenteerConfig.load(EXAMPLE_CITATIONS_INLINE)

    (entry,) = config.citations
    assert entry.label == "Dataset"
    assert entry.citation.type is CitationType.dataset
    assert entry.is_self is True
    assert entry.note == "Cite the DP2 dataset and this documentation."
    assert entry.citation.doi == "10.71929/rubin/2570308"
    assert entry.citation.title == "Data Preview 2"
    assert entry.citation.publisher == "Vera C. Rubin Observatory"
    assert entry.citation.date == PartialDate(2025, 6, 30)
    assert entry.citation.authors == (
        OrganizationAuthor(
            name="Vera C. Rubin Observatory", ror="https://ror.org/048g3cy84"
        ),
    )
    assert config.self_citation is entry


CITATION_CFF = """cff-version: 1.2.0
message: "If you use this software, please cite it as below."
title: "Example Software"
type: software
authors:
  - family-names: Sick
    given-names: Jonathan
    orcid: "https://orcid.org/0000-0003-3001-676X"
doi: 10.5281/zenodo.10385500
date-released: 2026-02-01
"""

EXAMPLE_CITATIONS_CFF = """

[project]
title = "Example Guide"

[[project.citations]]
cff = "../CITATION.cff"
self = true
label = "Software"
title = "Example Software, version 2"
"""


def test_citations_from_cff(tmp_path: Path) -> None:
    """A cff-sourced entry composes from the CITATION.cff file, and an
    inline field overrides the file's value.
    """
    (tmp_path / "CITATION.cff").write_text(CITATION_CFF)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    config = DocumenteerConfig.load(EXAMPLE_CITATIONS_CFF, root_dir=docs_dir)

    (entry,) = config.citations
    assert entry.label == "Software"
    # From the CITATION.cff file.
    assert entry.citation.type is CitationType.software
    assert entry.citation.doi == "10.5281/zenodo.10385500"
    assert entry.citation.date == PartialDate(2026, 2, 1)
    assert entry.citation.authors == (
        PersonAuthor(
            family_name="Sick",
            given_name="Jonathan",
            orcid="https://orcid.org/0000-0003-3001-676X",
        ),
    )
    # Set inline alongside cff, so it overrides the file's title.
    assert entry.citation.title == "Example Software, version 2"


EXAMPLE_CITATIONS_CFF_TYPE_OVERRIDE = """

[project]
title = "Example Guide"

[[project.citations]]
cff = "../CITATION.cff"
type = "dataset"
"""


def test_citations_type_overrides_cff(tmp_path: Path) -> None:
    """A type set alongside cff overrides the file's own, the way every
    other bibliographic field does.
    """
    (tmp_path / "CITATION.cff").write_text(CITATION_CFF)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    config = DocumenteerConfig.load(
        EXAMPLE_CITATIONS_CFF_TYPE_OVERRIDE, root_dir=docs_dir
    )

    (entry,) = config.citations
    assert entry.citation.type is CitationType.dataset


EXAMPLE_CITATIONS_TWO_SELF = """

[project]
title = "Example Guide"

[[project.citations]]
doi = "10.5281/zenodo.10385500"
self = true

[[project.citations]]
doi = "10.71929/rubin/2570308"
self = true
"""


def test_citations_two_self_entries_rejected() -> None:
    """A site is the landing page of at most one DOI."""
    with pytest.raises(ConfigError, match="self = true"):
        DocumenteerConfig.load(EXAMPLE_CITATIONS_TWO_SELF)


EXAMPLE_CITATIONS_TWO_PREFERRED = """

[project]
title = "Example Guide"

[[project.citations]]
doi = "10.5281/zenodo.10385500"
title = "A Dataset"
preferred = true

[[project.citations]]
doi = "10.71929/rubin/2570308"
title = "A Paper"
preferred = true
"""


def test_citations_two_preferred_entries_rejected() -> None:
    """A site asks readers to use one citation, so two entries claiming to be
    it is a configuration error rather than a silent first-wins.
    """
    with pytest.raises(ConfigError, match="preferred = true"):
        DocumenteerConfig.load(EXAMPLE_CITATIONS_TWO_PREFERRED)


EXAMPLE_CITATIONS_BAD_DOI = """

[project]
title = "Example Guide"

[[project.citations]]
doi = "not-a-doi"
title = "Example"
"""


def test_citations_malformed_doi_rejected() -> None:
    """A value that is not a DOI is rejected when the config is loaded."""
    with pytest.raises(ConfigError, match="Not a DOI"):
        DocumenteerConfig.load(EXAMPLE_CITATIONS_BAD_DOI)


EXAMPLE_CITATIONS_BAD_TYPE = """

[project]
title = "Example Guide"

[[project.citations]]
doi = "10.5281/zenodo.10385500"
title = "Example"
type = "preprint"
"""


def test_citations_unknown_type_rejected() -> None:
    """A type outside the vocabulary is rejected when the config is loaded,
    with a message naming the values that are accepted.
    """
    with pytest.raises(ConfigError) as exc_info:
        DocumenteerConfig.load(EXAMPLE_CITATIONS_BAD_TYPE)

    message = str(exc_info.value)
    for value in ("dataset", "article", "software", "report", "other"):
        assert value in message


EXAMPLE_CITATIONS_MISSING_CFF = """

[project]
title = "Example Guide"

[[project.citations]]
cff = "../CITATION.cff"
label = "Software"
"""


def test_citations_missing_cff_file(tmp_path: Path) -> None:
    """A cff path that names no file fails with an error naming the path."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    config = DocumenteerConfig.load(
        EXAMPLE_CITATIONS_MISSING_CFF, root_dir=docs_dir
    )

    with pytest.raises(ConfigError) as exc_info:
        _ = config.citations

    message = str(exc_info.value)
    assert "label 'Software'" in message
    assert str(tmp_path / "CITATION.cff") in message


EXAMPLE_CITATIONS_NO_DOI = """

[project]
title = "Example Guide"

[[project.citations]]
title = "Example"
"""


def test_citations_without_doi_rejected() -> None:
    """An entry that yields no DOI from either source is an error."""
    config = DocumenteerConfig.load(EXAMPLE_CITATIONS_NO_DOI)
    with pytest.raises(ConfigError, match="declares no DOI"):
        _ = config.citations


EXAMPLE_CITATIONS_FOOTER = """

[project]
title = "Example Guide"

[[project.citations]]
doi = "10.5281/zenodo.10385500"
label = "Paper"
title = "A Paper"

[[project.citations]]
doi = "10.71929/rubin/2570308"
label = "Site"
self = true

[[project.citations]]
doi = "10.5281/zenodo.10385501"
label = "Dataset"
title = "A Dataset"
in_footer = true
"""


EXAMPLE_CITATIONS_PREFERRED = """

[project]
title = "Butler Guide"

[[project.citations]]
doi = "10.1117/12.2629569"
label = "Paper"
type = "article"
preferred = true
title = "The Vera C. Rubin Observatory Data Butler"

[[project.citations]]
doi = "10.5281/zenodo.10385500"
label = "Dataset"
title = "A Dataset"
"""


def test_citations_preferred_without_self() -> None:
    """A site whose preferred citation is a work published elsewhere marks it
    `preferred`, which asks readers to cite it without claiming the site is
    its landing page.
    """
    config = DocumenteerConfig.load(EXAMPLE_CITATIONS_PREFERRED)

    preferred = config.preferred_citation
    assert preferred is not None
    assert preferred.label == "Paper"
    assert preferred.is_preferred is True
    assert preferred.is_self is False
    # Nothing claims the site as a landing page, so no page emits the
    # single-valued head metadata.
    assert config.self_citation is None
    assert [entry.in_footer for entry in config.citations] == [True, False]


def test_set_citations_preferred_without_self() -> None:
    """A site with a preferred citation but no self entry publishes the
    preferred entry alone: nothing claims the site as a landing page, so the
    head metadata has nothing to emit.
    """
    config = DocumenteerConfig.load(EXAMPLE_CITATIONS_PREFERRED)
    html_context: dict[str, Any] = {}
    config.set_citations(html_context)

    preferred = html_context["documenteer_preferred_citation"]
    assert preferred is not None
    assert preferred["label"] == "Paper"
    assert html_context["documenteer_self_citation"] is None


EXAMPLE_CITATIONS_SELF_AND_PREFERRED = """

[project]
title = "Example Guide"
base_url = "https://example.lsst.io"

[[project.citations]]
doi = "10.71929/rubin/2570308"
label = "Site"
self = true

[[project.citations]]
doi = "10.1117/12.2629569"
label = "Paper"
title = "A Paper"
preferred = true
"""


def test_citations_self_and_preferred_are_different_entries() -> None:
    """A site can be one DOI's landing page while asking readers to cite
    another work, and the two claims are answered by different entries.
    """
    config = DocumenteerConfig.load(EXAMPLE_CITATIONS_SELF_AND_PREFERRED)

    self_citation = config.self_citation
    preferred = config.preferred_citation
    assert self_citation is not None
    assert preferred is not None
    assert self_citation.label == "Site"
    assert preferred.label == "Paper"
    # An explicit preferred entry takes the footer default with it, so the
    # site shows the citation it asks readers to use.
    assert [entry.in_footer for entry in config.citations] == [False, True]


def test_citations_in_footer_defaults() -> None:
    """in_footer defaults to true only for the self entry, and the array
    order is preserved.
    """
    config = DocumenteerConfig.load(EXAMPLE_CITATIONS_FOOTER)

    assert [entry.label for entry in config.citations] == [
        "Paper",
        "Site",
        "Dataset",
    ]
    assert [entry.in_footer for entry in config.citations] == [
        False,
        True,
        True,
    ]
    self_citation = config.self_citation
    assert self_citation is not None
    assert self_citation.label == "Site"
    # The self entry takes its title from the project when it declares none.
    assert self_citation.citation.title == "Example Guide"


def test_set_citations_html_context() -> None:
    """set_citations publishes the resolved citations into html_context,
    including the plain-text and BibTeX renderings.
    """
    config = DocumenteerConfig.load(EXAMPLE_CITATIONS_INLINE)
    html_context: dict[str, Any] = {}
    config.set_citations(html_context)

    (context,) = html_context["documenteer_citations"]
    assert context["label"] == "Dataset"
    assert context["type"] == "dataset"
    assert context["is_self"] is True
    assert context["in_footer"] is True
    assert context["doi"] == "10.71929/rubin/2570308"
    assert context["doi_url"] == "https://doi.org/10.71929/rubin/2570308"
    assert context["year"] == 2025
    assert context["date"] == "2025-06-30"
    assert context["authors"] == [
        {
            "type": "organization",
            "name": "Vera C. Rubin Observatory",
            "citation_name": "Vera C. Rubin Observatory",
            "ror": "https://ror.org/048g3cy84",
        }
    ]
    assert context["plain_text"] == (
        "Vera C. Rubin Observatory (2025). Data Preview 2. "
        "Vera C. Rubin Observatory. https://doi.org/10.71929/rubin/2570308"
    )
    assert context["bibtex"].startswith("@misc{")
    assert "doi = {10.71929/rubin/2570308}" in context["bibtex"]
    assert html_context["documenteer_self_citation"] is context
    # The self entry is the preferred one by default, which is what keeps a
    # configuration written before `preferred` existed unchanged.
    assert html_context["documenteer_preferred_citation"] is context
    assert context["is_preferred"] is True


def test_set_citations_publishes_jsonld() -> None:
    """set_citations also publishes the citations as a serialized schema.org
    JSON-LD document, ready for the guide's <head>.
    """
    config = DocumenteerConfig.load(EXAMPLE_CITATIONS_INLINE)
    html_context: dict[str, Any] = {}
    config.set_citations(html_context)

    payload = json.loads(html_context["documenteer_citations_jsonld"])
    assert payload["@context"] == "https://schema.org"
    # The self citation declares type = "dataset", so the site is published
    # as a data release's landing page rather than as a plain WebSite.
    assert payload["@type"] == "Dataset"
    assert payload["@id"] == "https://doi.org/10.71929/rubin/2570308"
    assert payload["identifier"]["value"] == "10.71929/rubin/2570308"
    assert payload["name"] == "Data Preview 2"
    # The site's own base_url, not the doi.org redirect, is the node's url.
    assert payload["url"] == "https://dp0-2.lsst.io/"


def test_set_citations_without_citations() -> None:
    """A site without [[project.citations]] leaves html_context untouched."""
    config = DocumenteerConfig.load(EXAMPLE)
    assert config.citations == []
    assert config.self_citation is None

    html_context: dict[str, Any] = {}
    config.set_citations(html_context)
    assert html_context == {}


EXAMPLE_CITATIONS_NAMELESS_AUTHOR = """

[project]
title = "Example Guide"

[[project.citations]]
doi = "10.5281/zenodo.10385500"
title = "Example"
authors = [{ orcid = "0000-0003-3001-676X" }]
"""

EXAMPLE_CITATIONS_DOUBLE_NAMED_AUTHOR = """

[project]
title = "Example Guide"

[[project.citations]]
doi = "10.5281/zenodo.10385500"
title = "Example"
authors = [{ name = "Rubin Observatory", family_name = "Sick" }]
"""


@pytest.mark.parametrize(
    ("example", "match"),
    [
        (EXAMPLE_CITATIONS_NAMELESS_AUTHOR, "has no name"),
        (EXAMPLE_CITATIONS_DOUBLE_NAMED_AUTHOR, "both name and family_name"),
    ],
)
def test_citation_author_naming_rejected(example: str, match: str) -> None:
    """An author must be named either as an organization or as a person."""
    with pytest.raises(ConfigError, match=match):
        DocumenteerConfig.load(example)


EXAMPLE_CITATIONS_PAGES = """

[project]
title = "Data Preview 2 Documentation"
base_url = "https://dp2.lsst.io"

[[project.citations]]
doi = "10.71929/rubin/2570308"
label = "Release"
self = true

[[project.citations]]
doi = "10.71929/rubin/3382539"
label = "Object (Butler)"
type = "dataset"
page = "products/catalogs/object#butler"
title = "Object catalog (Butler)"

[[project.citations]]
doi = "10.71929/rubin/3382540"
label = "Object (TAP)"
type = "dataset"
page = "/products/catalogs/object#tap"
title = "Object catalog (TAP)"

[[project.citations]]
doi = "10.71929/rubin/3382541"
label = "Visit"
type = "dataset"
page = "products/catalogs/visit"
title = "Visit table"
"""


def test_citations_page_claims() -> None:
    """A page claim is split into the docname and its fragment, with a
    leading slash on the docname dropped; an entry that claims no page
    carries neither.
    """
    config = DocumenteerConfig.load(EXAMPLE_CITATIONS_PAGES)

    site, butler, tap, visit = config.citations
    assert site.page is None
    assert site.page_fragment is None
    assert butler.page == "products/catalogs/object"
    assert butler.page_fragment == "butler"
    assert tap.page == "products/catalogs/object"
    assert tap.page_fragment == "tap"
    assert visit.page == "products/catalogs/visit"
    assert visit.page_fragment is None


def test_citations_page_in_html_context() -> None:
    """The page claim reaches html_context, which is where the extension
    that rewrites a claimed page's metadata reads it from.
    """
    config = DocumenteerConfig.load(EXAMPLE_CITATIONS_PAGES)
    html_context: dict[str, Any] = {}
    config.set_citations(html_context)

    site, butler, _, visit = html_context["documenteer_citations"]
    assert site["page"] is None
    assert site["page_fragment"] is None
    assert butler["page"] == "products/catalogs/object"
    assert butler["page_fragment"] == "butler"
    assert visit["page"] == "products/catalogs/visit"
    assert visit["page_fragment"] is None


EXAMPLE_CITATIONS_DUPLICATE_PAGE = """

[project]
title = "Example Guide"

[[project.citations]]
doi = "10.71929/rubin/3382539"
title = "Object catalog (Butler)"
page = "products/object#tap"

[[project.citations]]
doi = "10.71929/rubin/3382540"
title = "Object catalog (TAP)"
page = "products/object#tap"
"""


def test_citations_duplicate_page_rejected() -> None:
    """Two entries that name the same docname *and* fragment claim the same
    landing page, which no page can be for two DOIs.
    """
    with pytest.raises(ConfigError, match="products/object#tap"):
        DocumenteerConfig.load(EXAMPLE_CITATIONS_DUPLICATE_PAGE)


EXAMPLE_CITATIONS_EMPTY_PAGE = """

[project]
title = "Example Guide"

[[project.citations]]
doi = "10.71929/rubin/3382539"
title = "Object catalog"
page = "#butler"
"""

EXAMPLE_CITATIONS_EMPTY_FRAGMENT = """

[project]
title = "Example Guide"

[[project.citations]]
doi = "10.71929/rubin/3382539"
title = "Object catalog"
page = "products/object#"
"""

EXAMPLE_CITATIONS_TWO_FRAGMENTS = """

[project]
title = "Example Guide"

[[project.citations]]
doi = "10.71929/rubin/3382539"
title = "Object catalog"
page = "products/object#butler#tap"
"""


@pytest.mark.parametrize(
    ("example", "match"),
    [
        (EXAMPLE_CITATIONS_EMPTY_PAGE, "names no page"),
        (EXAMPLE_CITATIONS_EMPTY_FRAGMENT, "empty fragment"),
        (EXAMPLE_CITATIONS_TWO_FRAGMENTS, "more than one"),
    ],
)
def test_citations_malformed_page_rejected(example: str, match: str) -> None:
    """A page claim is a docname with at most one non-empty fragment."""
    with pytest.raises(ConfigError, match=match):
        DocumenteerConfig.load(example)


CITATION_DATE_TEMPLATE = """

[project]
title = "Example Guide"

[[project.citations]]
doi = "10.5281/zenodo.10385500"
title = "Example"
self = true
date = {value}
"""


@pytest.mark.parametrize(
    ("written", "expected"),
    [
        ("2025-06-30", PartialDate(2025, 6, 30)),
        ("2025", PartialDate(2025)),
        ('"2025-06"', PartialDate(2025, 6)),
        ('"2025"', PartialDate(2025)),
    ],
)
def test_citation_date_keeps_the_precision_it_is_written_in(
    written: str, expected: PartialDate
) -> None:
    """A citation date is written as a TOML date, a bare year, or a quoted
    ISO 8601 date, and each is kept at the precision it states — TOML has a
    date type but no year or year-month type.
    """
    config = DocumenteerConfig.load(
        CITATION_DATE_TEMPLATE.format(value=written)
    )

    (entry,) = config.citations
    assert entry.citation.date == expected


@pytest.mark.parametrize(
    "written", ['"June 2025"', '"2025-13"', '"2025-06-00"', "20250", "true"]
)
def test_citation_date_rejects_a_value_that_is_not_a_date(
    written: str,
) -> None:
    """A value that is not one of the three forms is rejected with a message
    that names all three, rather than being read as some nearby date.
    """
    with pytest.raises(ConfigError, match=r"date = 2025-06-30"):
        DocumenteerConfig.load(CITATION_DATE_TEMPLATE.format(value=written))


@pytest.mark.parametrize(
    ("written", "published"),
    [("2025-06-30", "2025-06-30"), ("2025", "2025"), ('"2025-06"', "2025-06")],
)
def test_citation_json_ld_publishes_the_stated_precision(
    written: str, published: str
) -> None:
    """The schema.org ``datePublished`` a page carries is the date the
    configuration stated, never a day it filled in.
    """
    config = DocumenteerConfig.load(
        CITATION_DATE_TEMPLATE.format(value=written)
    )
    html_context: dict[str, Any] = {}
    config.set_citations(html_context)

    payload = json.loads(html_context["documenteer_citations_jsonld"])
    assert payload["datePublished"] == published


CITATION_CFF_YEAR = """cff-version: 1.2.0
message: "If you use this software, please cite it as below."
title: "Example Software"
type: software
preferred-citation:
  type: article
  title: "An article"
  doi: 10.5281/zenodo.10385500
  year: 2022
"""

EXAMPLE_CITATIONS_CFF_SELF = """

[project]
title = "Example Guide"

[[project.citations]]
cff = "../CITATION.cff"
self = true
"""


@pytest.mark.parametrize(
    ("extra", "published"),
    [("", "2022"), ("  month: 8\n", "2022-08")],
)
def test_cff_citation_publishes_the_files_precision(
    tmp_path: Path, extra: str, published: str
) -> None:
    """A CITATION.cff that dates a work to the year, or to the month, is
    published at that precision rather than at a day the file never wrote.
    """
    (tmp_path / "CITATION.cff").write_text(CITATION_CFF_YEAR + extra)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    config = DocumenteerConfig.load(
        EXAMPLE_CITATIONS_CFF_SELF, root_dir=docs_dir
    )
    html_context: dict[str, Any] = {}
    config.set_citations(html_context)

    payload = json.loads(html_context["documenteer_citations_jsonld"])
    assert payload["datePublished"] == published
