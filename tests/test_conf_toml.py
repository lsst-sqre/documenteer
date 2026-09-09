"""Test the documenteer.toml configuration support."""

from __future__ import annotations

import json
from importlib.metadata import version
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
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


CITATION_CFF_PREFERRED = """cff-version: 1.2.0
message: "If you use this software, please cite it as below."
title: "Example Software"
type: software
authors:
  - name: "Vera C. Rubin Observatory"
doi: 10.5281/zenodo.10385500
preferred-citation:
  type: article
  title: "An Example Paper"
  authors:
    - family-names: Sick
      given-names: Jonathan
  doi: 10.1117/12.2629569
  year: 2022
"""

EXAMPLE_CITATIONS_CFF_TOP_LEVEL = """

[project]
title = "Example Guide"

[[project.citations]]
cff = "../CITATION.cff"
cff_preferred = false
label = "Software"
"""


def test_citations_cff_top_level_record(tmp_path: Path) -> None:
    """``cff_preferred = false`` cites the software the repository is, rather
    than the paper its CITATION.cff prefers.
    """
    (tmp_path / "CITATION.cff").write_text(CITATION_CFF_PREFERRED)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    config = DocumenteerConfig.load(
        EXAMPLE_CITATIONS_CFF_TOP_LEVEL, root_dir=docs_dir
    )

    (entry,) = config.citations
    assert entry.citation.title == "Example Software"
    assert entry.citation.type is CitationType.software
    assert entry.citation.doi == "10.5281/zenodo.10385500"
    assert entry.citation.authors == (
        OrganizationAuthor(name="Vera C. Rubin Observatory"),
    )


EXAMPLE_CITATIONS_CFF_SELF_ON_PREFERRED = """

[project]
title = "Example Guide"

[[project.citations]]
cff = "../CITATION.cff"
self = true
label = "Paper"
"""


def test_citations_self_on_a_cff_preferred_citation_rejected(
    tmp_path: Path,
) -> None:
    """An entry that claims to be the landing page of the work its
    CITATION.cff prefers is rejected, since that work is by construction
    published somewhere else.

    ``self`` on such an entry is the mistake that publishes every page of
    the site as the full text of someone else's paper, and the field the
    author wanted is ``preferred``.
    """
    (tmp_path / "CITATION.cff").write_text(CITATION_CFF_PREFERRED)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    config = DocumenteerConfig.load(
        EXAMPLE_CITATIONS_CFF_SELF_ON_PREFERRED, root_dir=docs_dir
    )

    with pytest.raises(ConfigError) as exc_info:
        _ = config.citations

    message = str(exc_info.value)
    assert "label 'Paper'" in message
    assert "self = true" in message
    assert "preferred-citation" in message
    # The three ways out the message has to offer.
    assert "preferred = true" in message
    assert "cff_preferred = false" in message
    assert "cff_preferred = true" in message
    # Raised as a plain ConfigError rather than through pydantic, so a
    # sphinx-build prints the sentence above and nothing else — no
    # validation-error tail, and no "please report this" banner.
    assert type(exc_info.value) is ConfigError
    assert "Configuration error in documenteer.toml" not in message
    assert "validation error" not in message


EXAMPLE_CITATIONS_CFF_SELF_PREFERRED_ACKNOWLEDGED = """

[project]
title = "Example Guide"
base_url = "https://example.lsst.io/"

[[project.citations]]
cff = "../CITATION.cff"
self = true
cff_preferred = true
label = "Paper"
"""


def test_citations_self_on_an_acknowledged_cff_preference_accepted(
    tmp_path: Path,
) -> None:
    """Writing ``cff_preferred = true`` alongside ``self`` says the record
    was chosen on purpose, which is a claim a site is entitled to make.

    A paper whose CITATION.cff and documentation site are the same
    repository is the case: this site really is that DOI's landing page, and
    the head metadata describes the paper.
    """
    (tmp_path / "CITATION.cff").write_text(CITATION_CFF_PREFERRED)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    config = DocumenteerConfig.load(
        EXAMPLE_CITATIONS_CFF_SELF_PREFERRED_ACKNOWLEDGED, root_dir=docs_dir
    )

    self_citation = config.self_citation
    assert self_citation is not None
    assert self_citation.citation.title == "An Example Paper"
    assert self_citation.citation.doi == "10.1117/12.2629569"

    html_context: dict[str, Any] = {}
    config.set_citations(html_context)
    assert html_context["documenteer_self_citation_metatags"].splitlines() == [
        '<meta name="citation_title" content="An Example Paper">',
        '<meta name="citation_author" content="Sick, Jonathan">',
        '<meta name="citation_publication_date" content="2022">',
        '<meta name="citation_doi" content="10.1117/12.2629569">',
        '<meta name="citation_fulltext_html_url" '
        'content="https://example.lsst.io/">',
        '<meta name="DC.identifier" '
        'content="https://doi.org/10.1117/12.2629569">',
    ]


EXAMPLE_CITATIONS_CFF_SELF_TOP_LEVEL = """

[project]
title = "Example Guide"

[[project.citations]]
cff = "../CITATION.cff"
self = true
cff_preferred = false
label = "Software"
"""


def test_citations_self_on_a_cff_top_level_record_accepted(
    tmp_path: Path,
) -> None:
    """``cff_preferred = false`` reads the record that describes the
    repository, which is a work this site may well be the landing page of.
    """
    (tmp_path / "CITATION.cff").write_text(CITATION_CFF_PREFERRED)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    config = DocumenteerConfig.load(
        EXAMPLE_CITATIONS_CFF_SELF_TOP_LEVEL, root_dir=docs_dir
    )

    self_citation = config.self_citation
    assert self_citation is not None
    assert self_citation.citation.title == "Example Software"
    assert self_citation.citation.doi == "10.5281/zenodo.10385500"


EXAMPLE_CITATIONS_CFF_PREFERRED_ENTRY = """

[project]
title = "Example Guide"

[[project.citations]]
cff = "../CITATION.cff"
preferred = true
label = "Paper"
"""


def test_citations_preferred_on_a_cff_preferred_citation_accepted(
    tmp_path: Path,
) -> None:
    """The documented pattern — ask readers to cite the paper the file
    prefers, and claim nothing about where its DOI resolves — is untouched
    by the rule ``self`` is held to.
    """
    (tmp_path / "CITATION.cff").write_text(CITATION_CFF_PREFERRED)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    config = DocumenteerConfig.load(
        EXAMPLE_CITATIONS_CFF_PREFERRED_ENTRY, root_dir=docs_dir
    )

    (entry,) = config.citations
    assert entry.is_preferred is True
    assert entry.is_self is False
    assert entry.citation.title == "An Example Paper"
    assert config.self_citation is None


EXAMPLE_CITATIONS_CFF_PREFERRED_WITHOUT_CFF = """

[project]
title = "Example Guide"

[[project.citations]]
doi = "10.5281/zenodo.10385500"
title = "Example Software"
cff_preferred = false
"""


def test_citations_cff_preferred_without_cff_rejected() -> None:
    """``cff_preferred`` chooses which record of a CITATION.cff file is read,
    so an entry that sets it without naming a file states a preference over
    nothing.
    """
    with pytest.raises(ConfigError) as exc_info:
        DocumenteerConfig.load(EXAMPLE_CITATIONS_CFF_PREFERRED_WITHOUT_CFF)

    message = str(exc_info.value)
    assert "cff_preferred" in message
    assert "cff" in message


SOFTWARE_RECORD_CFF_PATH = (
    Path(__file__).parent / "data" / "citationcff" / "software-record.cff"
)
"""A CITATION.cff shaped like ``lsst/daf_butler``'s: a top-level software
record with a repository and no DOI, above a preferred citation for the paper
that describes it.

Like that file, it declares no top-level ``type`` — CFF makes the key
optional and defaults it to ``software`` — so an entry reading its top-level
record is typed by that default rather than by anything the file states.
"""

EXAMPLE_CITATIONS_CFF_SOFTWARE = """

[project]
title = "Butler Guide"

[[project.citations]]
cff = "../CITATION.cff"
cff_preferred = false
label = "Software"
"""


def test_citations_cff_software_located_by_its_repository(
    tmp_path: Path,
) -> None:
    """A repository whose CITATION.cff prefers a paper can still cite the
    software itself, which a DOI-less file locates by its repository.
    """
    (tmp_path / "CITATION.cff").write_text(
        SOFTWARE_RECORD_CFF_PATH.read_text(encoding="utf-8")
    )
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    config = DocumenteerConfig.load(
        EXAMPLE_CITATIONS_CFF_SOFTWARE, root_dir=docs_dir
    )

    (entry,) = config.citations
    assert entry.citation.title == "daf_butler"
    assert entry.citation.doi is None
    assert entry.citation.url == "https://github.com/lsst/daf_butler"


EXAMPLE_CITATIONS_CFF_SOFTWARE_DOCUMENTED = """

[project]
title = "Butler Guide"

[[project.citations]]
cff = "../CITATION.cff"
cff_preferred = false
label = "Software"
in_footer = true
note = "Cite the version you ran; this page names the version it documents."
"""
"""The ``cff_preferred = false`` entry the citations guide documents, written
exactly as that page writes it — no inline ``type``.
"""


def test_citations_cff_untyped_software_composes_as_software(
    tmp_path: Path,
) -> None:
    """The documented ``cff_preferred = false`` entry, against a file that
    declares no top-level type, publishes the software the repository is.

    This is the composed end of CFF's top-level default: without it the entry
    would compose as a BibTeX ``@misc`` and a schema.org ``CreativeWork``,
    which is neither what the repository is nor what the guide's example
    promises.
    """
    (tmp_path / "CITATION.cff").write_text(
        SOFTWARE_RECORD_CFF_PATH.read_text(encoding="utf-8")
    )
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    config = DocumenteerConfig.load(
        EXAMPLE_CITATIONS_CFF_SOFTWARE_DOCUMENTED, root_dir=docs_dir
    )
    html_context: dict[str, Any] = {}
    config.set_citations(html_context)

    (entry,) = config.citations
    assert entry.citation.type is CitationType.software
    assert entry.citation.to_bibtex().startswith("@software{")
    payload = json.loads(html_context["documenteer_citations_jsonld"])
    (node,) = payload["citation"]
    assert node["@type"] == "SoftwareSourceCode"


def test_citations_cff_provenance_reaches_the_html_context(
    tmp_path: Path,
) -> None:
    """A cff-sourced entry carries which file and which record supplied its
    fields, so a build reporting a field neither source states can name where
    the value belongs.

    The software record of this file dates nothing — no date-released, no
    date-published, no year — where its preferred citation is dated, which is
    why the record has to be carried alongside the path.
    """
    (tmp_path / "CITATION.cff").write_text(
        SOFTWARE_RECORD_CFF_PATH.read_text(encoding="utf-8")
    )
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    config = DocumenteerConfig.load(
        EXAMPLE_CITATIONS_CFF_SOFTWARE, root_dir=docs_dir
    )

    (entry,) = config.citations
    assert entry.citation.date is None
    # The path as documenteer.toml wrote it, which is what an author edits.
    assert entry.cff == "../CITATION.cff"
    assert entry.cff_preferred is False
    context = entry.to_html_context()
    assert context["date"] is None
    assert context["cff"] == "../CITATION.cff"
    assert context["cff_preferred"] is False


def test_citations_inline_entry_has_no_cff_provenance() -> None:
    """An entry that states its own fields names no file, so a build reporting
    a missing field offers only the entry's own field as the fix.
    """
    config = DocumenteerConfig.load(EXAMPLE_CITATIONS_INLINE)

    (entry,) = config.citations
    assert entry.cff is None
    assert entry.to_html_context()["cff"] is None


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


EXAMPLE_CITATIONS_CFF_TOP_LEVEL_TYPE_OVERRIDE = """

[project]
title = "Example Guide"

[[project.citations]]
cff = "../CITATION.cff"
cff_preferred = false
type = "dataset"
"""


def test_citations_type_overrides_cff_top_level_default(
    tmp_path: Path,
) -> None:
    """A type set alongside cff overrides the software type a top-level
    record with no type of its own is read as, the same way it overrides a
    type the file states.
    """
    (tmp_path / "CITATION.cff").write_text(
        SOFTWARE_RECORD_CFF_PATH.read_text(encoding="utf-8")
    )
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    config = DocumenteerConfig.load(
        EXAMPLE_CITATIONS_CFF_TOP_LEVEL_TYPE_OVERRIDE, root_dir=docs_dir
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


def test_citations_without_doi_or_url_rejected() -> None:
    """An entry that yields neither a DOI nor a URL from any source is an
    error naming both fields, since either would locate the work.
    """
    config = DocumenteerConfig.load(EXAMPLE_CITATIONS_NO_DOI)
    with pytest.raises(ConfigError) as exc_info:
        _ = config.citations

    message = str(exc_info.value)
    assert "neither a DOI nor a URL" in message
    assert "Set doi or url" in message


EXAMPLE_CITATIONS_CFF_BLANK_URL = """

[project]
title = "Example Guide"

[[project.citations]]
cff = "../CITATION.cff"
label = "Software"
"""


def test_citations_cff_blank_url_is_no_location(tmp_path: Path) -> None:
    """A CITATION.cff whose url holds only whitespace supplies no landing
    page, so an entry reading it and declaring no DOI is rejected as
    unlocatable rather than building a citation that renders without a link.

    The reader treats every field that collapses to nothing as absent, so a
    blank one arrives here as `None` — the same shape the field validator
    guarantees for a url written inline — and the entry falls to the check
    that names both fields.
    """
    (tmp_path / "CITATION.cff").write_text(
        'cff-version: 1.2.0\ntitle: A package\ntype: software\nurl: "   "\n'
    )
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    config = DocumenteerConfig.load(
        EXAMPLE_CITATIONS_CFF_BLANK_URL, root_dir=docs_dir
    )

    with pytest.raises(ConfigError) as exc_info:
        _ = config.citations

    assert "neither a DOI nor a URL" in str(exc_info.value)


EXAMPLE_CITATIONS_SELF_WITHOUT_DOI = """

[project]
title = "Example Guide"

[[project.citations]]
title = "Example"
url = "https://example.lsst.io/"
self = true
"""


def test_citations_self_without_doi_rejected() -> None:
    """The self entry is the claim to be a DOI's landing page, so a URL does
    not stand in for the DOI it would resolve to.
    """
    config = DocumenteerConfig.load(EXAMPLE_CITATIONS_SELF_WITHOUT_DOI)
    with pytest.raises(ConfigError) as exc_info:
        _ = config.citations

    message = str(exc_info.value)
    assert "self = true" in message
    assert "declares no DOI" in message


EXAMPLE_CITATIONS_URL_ONLY = """

[project]
title = "Example Guide"

[[project.citations]]
title = "Example Software"
type = "software"
url = "https://github.com/lsst/daf_butler"
"""


def test_citations_url_stands_in_for_a_doi() -> None:
    """A work with no DOI is citable by its landing page, which is how CFF
    and GitHub cite software that has never been deposited.
    """
    config = DocumenteerConfig.load(EXAMPLE_CITATIONS_URL_ONLY)

    (entry,) = config.citations
    assert entry.citation.doi is None
    assert entry.citation.url == "https://github.com/lsst/daf_butler"


CITATION_URL_TEMPLATE = """

[project]
title = "Example Guide"

[[project.citations]]
title = "Example Software"
url = "{value}"
"""


@pytest.mark.parametrize(
    ("written", "match"),
    [
        ("", "url is empty"),
        ("  ", "url is empty"),
        ("github.com/lsst/daf_butler", "is not an absolute URL"),
        ("/datasets/dp1", "is not an absolute URL"),
        ("ftp://example.org/dp1.tar", "starts with ftp: rather than"),
        ("mailto:data@example.org", "starts with mailto: rather than"),
        ("localhost:8080/dp1", "starts with localhost: rather than"),
        ("C:/data/dp1", "starts with C: rather than"),
        ("https:///datasets/dp1", "names no host"),
    ],
)
def test_citations_unlinkable_url_rejected(written: str, match: str) -> None:
    """A url that is not an absolute http(s) URL is rejected when the
    configuration loads, rather than reaching a rendered citation.

    A blank one is the case that would otherwise pass silently: it is truthy,
    so it satisfies the entry-level check that a work is locatable, and only
    reduces to nothing where the citation is composed -- a plain-text
    citation ending in a bare period, a BibTeX entry with neither ``url`` nor
    ``doi``, and a JSON-LD node with no ``@id``. A scheme-less or root-
    relative one is read as a path instead: the footer and the citation card
    link it relative to whatever page is being rendered, and it reaches the
    JSON-LD node as a relative IRI.

    Each failure names itself: an ``ftp`` or ``mailto`` URL *is* absolute, so
    reporting it as "not an absolute URL" would send its author looking for a
    scheme they already wrote.
    """
    with pytest.raises(ConfigError, match=match):
        DocumenteerConfig.load(CITATION_URL_TEMPLATE.format(value=written))


EXAMPLE_CITATIONS_PADDED_URL = """

[project]
title = "Example Guide"

[[project.citations]]
title = "Example Software"
url = "  https://github.com/lsst/daf_butler  "
"""


def test_citations_url_is_stripped() -> None:
    """Whitespace around a url is removed, so the value the locatable check
    sees is the value the citation renders.
    """
    config = DocumenteerConfig.load(EXAMPLE_CITATIONS_PADDED_URL)

    (entry,) = config.citations
    assert entry.citation.url == "https://github.com/lsst/daf_butler"


CITATION_VERSION_TEMPLATE = """

[project]
title = "Example Guide"

[[project.citations]]
title = "Safir"
type = "software"
url = "https://github.com/lsst-sqre/safir"
version = "{value}"
"""


def test_citations_version_is_read() -> None:
    """An entry's version reaches the composed citation, which is what makes
    a software citation name the release a reader ran.
    """
    config = DocumenteerConfig.load(
        CITATION_VERSION_TEMPLATE.format(value="12.3.0")
    )

    (entry,) = config.citations
    assert entry.citation.version == "12.3.0"


def test_citations_version_is_collapsed() -> None:
    """Whitespace around a version is removed, so the value a citation
    renders is the version and not the spacing around it.
    """
    config = DocumenteerConfig.load(
        CITATION_VERSION_TEMPLATE.format(value="  12.3.0  ")
    )

    (entry,) = config.citations
    assert entry.citation.version == "12.3.0"


@pytest.mark.parametrize("written", ["", "   "])
def test_citations_blank_version_rejected(written: str) -> None:
    """A blank version is rejected where it is written rather than reduced to
    nothing where the citation is composed.

    It is the value that would otherwise pass silently: it is truthy, so it
    reads as a version that was stated, and it also suppresses the default a
    software entry would otherwise inherit from the project's own version —
    leaving the citation with no version at all and nothing to say why.
    """
    with pytest.raises(ConfigError, match="version is empty"):
        DocumenteerConfig.load(CITATION_VERSION_TEMPLATE.format(value=written))


CITATION_CFF_VERSIONED = """cff-version: 1.2.0
message: "If you use this software, please cite it as below."
title: "Example Software"
type: software
version: 9.9.9
authors:
  - name: "Vera C. Rubin Observatory"
repository-code: https://github.com/lsst-sqre/safir
"""
"""A CITATION.cff whose top-level software record states its release, which
is the shape a package's own file has."""


EXAMPLE_CITATIONS_CFF_VERSION = """

[project]
title = "Example Guide"

[[project.citations]]
cff = "../CITATION.cff"
cff_preferred = false
label = "Software"
"""


def test_citations_version_comes_from_cff(tmp_path: Path) -> None:
    """A CITATION.cff file's version supplies the entry's, so a package that
    already records its release in that file does not restate it.
    """
    (tmp_path / "CITATION.cff").write_text(CITATION_CFF_VERSIONED)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    config = DocumenteerConfig.load(
        EXAMPLE_CITATIONS_CFF_VERSION, root_dir=docs_dir
    )

    (entry,) = config.citations
    assert entry.citation.version == "9.9.9"


EXAMPLE_CITATIONS_CFF_VERSION_OVERRIDE = """

[project]
title = "Example Guide"

[[project.citations]]
cff = "../CITATION.cff"
cff_preferred = false
label = "Software"
version = "12.3.0"
"""


def test_citations_version_overrides_cff(tmp_path: Path) -> None:
    """A version set alongside cff overrides the file's own, the way every
    other bibliographic field does.
    """
    (tmp_path / "CITATION.cff").write_text(CITATION_CFF_VERSIONED)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    config = DocumenteerConfig.load(
        EXAMPLE_CITATIONS_CFF_VERSION_OVERRIDE, root_dir=docs_dir
    )

    (entry,) = config.citations
    assert entry.citation.version == "12.3.0"


VERSIONED_PROJECT = """

[project]
title = "Example Guide"
version = "4.5.6"
"""
"""A project whose own version resolves from ``[project] version``, which is
what a software citation of this site's package defaults to."""


DEFAULTED_VERSION_ENTRIES = {
    "self": """
[[project.citations]]
doi = "10.5281/zenodo.10385500"
type = "software"
self = true
title = "Example Software"
""",
    "preferred": """
[[project.citations]]
url = "https://github.com/lsst-sqre/safir"
type = "software"
preferred = true
title = "Example Software"
""",
}
"""The two inline shapes that describe this site's own package. The
``cff_preferred = false`` shape is the third, and is exercised against a
file below."""


@pytest.mark.parametrize("role", sorted(DEFAULTED_VERSION_ENTRIES))
def test_citations_software_defaults_to_the_project_version(
    role: str,
) -> None:
    """A software entry that describes this site's own package — the one it
    is the landing page of, or the one it asks readers to cite — names the
    release the site documents when nothing else states one.
    """
    config = DocumenteerConfig.load(
        VERSIONED_PROJECT + DEFAULTED_VERSION_ENTRIES[role]
    )

    (entry,) = config.citations
    assert entry.citation.version == "4.5.6"
    assert "(version 4.5.6)" in entry.citation.to_plain_text()


EXAMPLE_CITATIONS_CFF_VERSIONED_PROJECT = """

[project]
title = "Example Guide"
version = "4.5.6"

[[project.citations]]
cff = "../CITATION.cff"
cff_preferred = false
label = "Software"
"""


def test_citations_cff_top_level_software_defaults_to_the_project_version(
    tmp_path: Path,
) -> None:
    """``cff_preferred = false`` reads the repository's own record, so that
    entry is this site's package too and defaults the same way.
    """
    (tmp_path / "CITATION.cff").write_text(CITATION_CFF)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    config = DocumenteerConfig.load(
        EXAMPLE_CITATIONS_CFF_VERSIONED_PROJECT, root_dir=docs_dir
    )

    (entry,) = config.citations
    assert entry.citation.version == "4.5.6"


EXAMPLE_CITATIONS_PYTHON_PACKAGE = """

[project]
title = "Example Guide"

[project.python]
package = "documenteer"

[[project.citations]]
url = "https://github.com/lsst-sqre/documenteer"
type = "software"
preferred = true
title = "Documenteer"
"""


def test_citations_version_defaults_from_package_metadata() -> None:
    """A site that names its Python package rather than a literal version
    defaults from the installed distribution, so the citation names the
    release the docs were built from — a development build included, since
    that is what the page documents.
    """
    config = DocumenteerConfig.load(EXAMPLE_CITATIONS_PYTHON_PACKAGE)

    (entry,) = config.citations
    assert entry.citation.version == version("documenteer")


EXAMPLE_CITATIONS_OTHER_SOFTWARE = """

[project]
title = "Example Guide"
version = "4.5.6"

[[project.citations]]
url = "https://github.com/lsst/pipelines"
type = "software"
label = "Pipelines"
in_footer = true
title = "LSST Science Pipelines"
"""


def test_citations_other_software_never_defaults_a_version() -> None:
    """Software this site merely cites is somebody else's, whose releases the
    site knows nothing about, so it is left version-less rather than labelled
    with the version of the software that builds the site.
    """
    config = DocumenteerConfig.load(EXAMPLE_CITATIONS_OTHER_SOFTWARE)

    (entry,) = config.citations
    assert entry.citation.version is None


@pytest.mark.parametrize("citation_type", ["dataset", "article", "report"])
def test_citations_non_software_never_defaults_a_version(
    citation_type: str,
) -> None:
    """Only software defaults. A dataset's or a paper's release has nothing
    to do with the version of the software that builds the site, even when
    this site is its landing page.
    """
    config = DocumenteerConfig.load(
        VERSIONED_PROJECT
        + f"""
[[project.citations]]
doi = "10.5281/zenodo.10385500"
type = "{citation_type}"
self = true
title = "A Work"
"""
    )

    (entry,) = config.citations
    assert entry.citation.version is None


EXAMPLE_CITATIONS_UNVERSIONED_PROJECT = """

[project]
title = "Example Guide"

[[project.citations]]
url = "https://github.com/lsst-sqre/safir"
type = "software"
preferred = true
title = "Example Software"
"""


def test_citations_latest_is_not_a_version() -> None:
    """A site that declares neither a version nor a Python package resolves
    its version to the literal "Latest", which names a docs build rather than
    a release and must never reach a citation.
    """
    config = DocumenteerConfig.load(EXAMPLE_CITATIONS_UNVERSIONED_PROJECT)

    assert config.version == "Latest"
    (entry,) = config.citations
    assert entry.citation.version is None
    assert "version" not in entry.citation.to_plain_text()


CITATION_KEY_TEMPLATE = """

[project]
title = "Example Guide"
base_url = "https://example.lsst.io"

[[project.citations]]
doi = "10.71929/rubin/3382528"
type = "article"
title = "The Vera C. Rubin Observatory Data Butler"
bibtex_key = {value}
"""
"""A single non-self citation whose key is pinned, so the pinned key is the
only thing under test."""


def test_citations_bibtex_key_is_pinned() -> None:
    """A ``bibtex_key`` set on an entry is the key its BibTeX entry is
    written under, which is what lets a manuscript that copied the entry keep
    citing it after the metadata changes.
    """
    config = DocumenteerConfig.load(
        CITATION_KEY_TEMPLATE.format(value='"RTN-115"')
    )

    (entry,) = config.citations
    assert entry.bibtex_key == "RTN-115"
    assert entry.to_html_context()["bibtex"].startswith("@article{RTN-115,\n")


@pytest.mark.parametrize(
    "written",
    [
        '"RTN 115"',
        '"RTN,115"',
        '"RTN{115}"',
        '"RTN(115)"',
        '"RTN#115"',
        '"RTN%115"',
        '"RTN~115"',
        "'RTN\\115'",
        '"RTN\\"115"',
        '""',
        '"   "',
        '"RTN天115"',
    ],
)
def test_citations_malformed_bibtex_key_rejected(written: str) -> None:
    r"""A key BibTeX cannot read is rejected where it is written, rather than
    composing an entry that breaks the .bib file a reader pastes it into.

    Every value here either ends the key early (a comma, a brace, a
    parenthesis, whitespace), means something else to BibTeX or LaTeX (``#``,
    ``%``, ``~``, ``\``, ``"``), is no key at all, or is not ASCII.
    """
    with pytest.raises(ConfigError, match="bibtex_key"):
        DocumenteerConfig.load(CITATION_KEY_TEMPLATE.format(value=written))


@pytest.mark.parametrize(
    "written", ["SQR-000", "10.71929/rubin/3382528", "a.b:c_d"]
)
def test_citations_bibtex_key_accepts_punctuation_bibtex_reads(
    written: str,
) -> None:
    """``/``, ``.``, ``-``, ``:``, and ``_`` are ordinary key characters —
    lsst.bib keys its DataCite records by DOI — so a key carrying them is
    accepted as written.
    """
    config = DocumenteerConfig.load(
        CITATION_KEY_TEMPLATE.format(value=f'"{written}"')
    )

    (entry,) = config.citations
    assert entry.bibtex_key == written


EXAMPLE_CITATIONS_KEY_POLICY = """

[project]
title = "Data Preview 2 Documentation"
base_url = "https://dp2.lsst.io"

[[project.citations]]
doi = "10.71929/rubin/2570308"
label = "Release"
type = "dataset"
self = true
title = "Data Preview 2"

[[project.citations]]
doi = "10.71929/rubin/3382540"
label = "Object (TAP)"
type = "dataset"
title = "Object catalog (TAP)"

[[project.citations]]
url = "https://github.com/lsst/daf_butler"
label = "Software"
type = "software"
title = "The Vera C. Rubin Observatory Data Butler"
authors = [{ family_name = "Jenness", given_name = "Tim" }]
date = 2022
"""
"""A site's own work, a work it publishes a DOI for, and a work it merely
cites -- one entry per branch of the key policy."""


def test_citations_own_work_is_keyed_by_the_lsst_io_subdomain() -> None:
    """The site's own work is keyed by the subdomain it is published at,
    which is what a reader at Rubin already calls it, even though the entry
    has a DOI of its own.
    """
    config = DocumenteerConfig.load(EXAMPLE_CITATIONS_KEY_POLICY)

    own, *_ = config.citations
    assert own.bibtex_key == "dp2"
    assert own.to_html_context()["bibtex"].startswith("@dataset{dp2,\n")


def test_citations_a_doi_bearing_entry_is_keyed_by_its_doi() -> None:
    """Every entry but the site's own is keyed by its DOI, verbatim, which
    is how lsst.bib keys the DataCite records a reader's .bib file already
    holds.
    """
    _, dataset, _ = DocumenteerConfig.load(
        EXAMPLE_CITATIONS_KEY_POLICY
    ).citations

    assert dataset.bibtex_key == "10.71929/rubin/3382540"


def test_citations_a_doi_less_entry_falls_back_to_author_year_title() -> None:
    """A work with no DOI has nothing to key it by but its own metadata, so
    it takes the composed author-year-title key -- with the article the
    title opens with skipped.
    """
    *_, software = DocumenteerConfig.load(
        EXAMPLE_CITATIONS_KEY_POLICY
    ).citations

    assert software.bibtex_key == "jenness2022vera"


CITATION_KEY_BASE_URL_TEMPLATE = """

[project]
title = "Example Guide"
{base_url}

[[project.citations]]
doi = "10.71929/rubin/2570308"
self = true
title = "Example Work"
"""

DOI_KEY = "10.71929/rubin/2570308"
"""The key the site's own work falls back to when no subdomain names it."""


@pytest.mark.parametrize(
    ("base_url", "expected"),
    [
        ('base_url = "https://dp2.lsst.io"', "dp2"),
        ('base_url = "https://safir.lsst.io/"', "safir"),
        ('base_url = "https://pipelines.lsst.io"', "pipelines"),
        ('base_url = "https://dp0-2.lsst.io"', "dp0-2"),
        ('base_url = "https://DP2.LSST.IO"', "dp2"),
        # A versioned build is one of many sharing the subdomain, so the
        # subdomain does not name this work.
        ('base_url = "https://pipelines.lsst.io/v/daily/"', DOI_KEY),
        ('base_url = "https://sub.dp2.lsst.io"', DOI_KEY),
        ('base_url = "https://lsst.io"', DOI_KEY),
        ('base_url = "https://github.com/lsst/daf_butler"', DOI_KEY),
        ("", DOI_KEY),
    ],
)
def test_citations_subdomain_key_needs_an_lsst_io_root(
    base_url: str, expected: str
) -> None:
    """Only a site published at the root of a single-label lsst.io host is
    named by its subdomain; every other site keys its own work by its DOI.
    """
    config = DocumenteerConfig.load(
        CITATION_KEY_BASE_URL_TEMPLATE.format(base_url=base_url)
    )

    (own,) = config.citations
    assert own.bibtex_key == expected


EXAMPLE_CITATIONS_KEY_PREFERRED = """

[project]
title = "Preferred Citation Guide"
base_url = "https://example.lsst.io"

[[project.citations]]
doi = "10.1117/12.2629569"
label = "Paper"
type = "article"
preferred = true
title = "The Vera C. Rubin Observatory Data Butler"

[[project.citations]]
doi = "10.71929/rubin/3382539"
label = "Dataset"
type = "dataset"
title = "Butler test dataset"
"""


def test_citations_subdomain_key_falls_to_the_preferred_entry() -> None:
    """A site that publishes no DOI of its own still asks readers to cite
    one work, so the subdomain names that work rather than going unused.
    """
    preferred, dataset = DocumenteerConfig.load(
        EXAMPLE_CITATIONS_KEY_PREFERRED
    ).citations

    assert preferred.bibtex_key == "example"
    assert dataset.bibtex_key == "10.71929/rubin/3382539"


EXAMPLE_CITATIONS_KEY_NO_OWN_WORK = """

[project]
title = "Example Guide"
base_url = "https://example.lsst.io"

[[project.citations]]
doi = "10.71929/rubin/3382539"
label = "Dataset"
type = "dataset"
in_footer = true
title = "Butler test dataset"
"""


def test_citations_subdomain_key_needs_an_entry_to_name() -> None:
    """A site that neither publishes a DOI nor names a preferred citation
    describes no work of its own, so no entry is keyed by the subdomain and
    the subdomain is not spent on a work the site merely cites.
    """
    (entry,) = DocumenteerConfig.load(
        EXAMPLE_CITATIONS_KEY_NO_OWN_WORK
    ).citations

    assert entry.bibtex_key == "10.71929/rubin/3382539"


EXAMPLE_CITATIONS_COLLIDING_KEYS = """

[project]
title = "Example Guide"

[[project.citations]]
url = "https://github.com/lsst/daf_butler"
label = "Butler"
type = "software"
title = "The Butler"
authors = [{ family_name = "Jenness", given_name = "Tim" }]
date = 2022

[[project.citations]]
url = "https://github.com/lsst/daf_butler/tree/v2"
label = "Butler v2"
type = "software"
title = "A Butler, Revisited"
authors = [{ family_name = "Jenness", given_name = "Tim" }]
date = 2022
"""


def test_citations_colliding_bibtex_keys_rejected() -> None:
    """Two entries that resolve to one key would overwrite each other in the
    .bib file a reader pastes them into, so the build names both entries and
    says which field tells them apart.
    """
    config = DocumenteerConfig.load(EXAMPLE_CITATIONS_COLLIDING_KEYS)

    with pytest.raises(ConfigError) as excinfo:
        _ = config.citations

    message = str(excinfo.value)
    assert "'Butler'" in message
    assert "'Butler v2'" in message
    assert "jenness2022butler" in message
    assert "bibtex_key" in message


EXAMPLE_CITATIONS_KEY_PINNED_ONTO_ANOTHER = """

[project]
title = "Example Guide"
base_url = "https://example.lsst.io"

[[project.citations]]
doi = "10.71929/rubin/2570308"
label = "Release"
self = true
title = "Example Release"

[[project.citations]]
doi = "10.71929/rubin/3382539"
label = "Dataset"
bibtex_key = "example"
title = "Butler test dataset"
"""


def test_citations_pinned_key_colliding_with_a_default_rejected() -> None:
    """A pinned key is checked against the keys the other entries resolve
    to, not only against other pinned ones, so taking the subdomain key of
    the site's own work is reported rather than silently duplicated.
    """
    config = DocumenteerConfig.load(EXAMPLE_CITATIONS_KEY_PINNED_ONTO_ANOTHER)

    with pytest.raises(ConfigError, match="'example'"):
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
    # Both default into the footer, in array order: the site is a landing
    # page, which DataCite asks to display the citation of the DOI it is the
    # landing page of, and it also asks readers to cite the paper.
    assert [entry.in_footer for entry in config.citations] == [True, True]


EXAMPLE_CITATIONS_SELF_OUT_OF_FOOTER = """

[project]
title = "Example Guide"
base_url = "https://example.lsst.io"

[[project.citations]]
doi = "10.71929/rubin/2570308"
label = "Site"
self = true
in_footer = false

[[project.citations]]
doi = "10.1117/12.2629569"
label = "Paper"
title = "A Paper"
preferred = true
"""


def test_citations_self_can_opt_out_of_the_footer() -> None:
    """A site that wants one footer citation rather than two writes
    in_footer = false, and the explicit value wins over the default.
    """
    config = DocumenteerConfig.load(EXAMPLE_CITATIONS_SELF_OUT_OF_FOOTER)

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
    # The entry declares type = "dataset", so it copies out as the biblatex
    # @dataset entry rather than as the generic @misc.
    assert context["bibtex"].startswith("@dataset{dp0-2,\n")
    assert context["bibtex_key"] == "dp0-2"
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


def test_set_citations_publishes_highwire_tags() -> None:
    """set_citations also publishes the self citation's Highwire meta tags,
    composed against the site's own base URL, ready for the guide's <head>.
    """
    config = DocumenteerConfig.load(EXAMPLE_CITATIONS_INLINE)
    html_context: dict[str, Any] = {}
    config.set_citations(html_context)

    assert html_context["documenteer_self_citation_metatags"].splitlines() == [
        '<meta name="citation_title" content="Data Preview 2">',
        '<meta name="citation_author" content="Vera C. Rubin Observatory">',
        '<meta name="citation_publication_date" content="2025/06/30">',
        '<meta name="citation_doi" content="10.71929/rubin/2570308">',
        '<meta name="citation_publisher" content="Vera C. Rubin Observatory">',
        '<meta name="citation_fulltext_html_url" '
        'content="https://dp0-2.lsst.io/">',
        '<meta name="DC.identifier" '
        'content="https://doi.org/10.71929/rubin/2570308">',
    ]


def test_set_citations_without_a_self_entry_emits_no_tags() -> None:
    """A site with a preferred citation but no self entry is no DOI's landing
    page, so it publishes no meta tags at all — not even the title and authors
    of the work it asks readers to cite, which is published elsewhere.
    """
    config = DocumenteerConfig.load(EXAMPLE_CITATIONS_PREFERRED)
    html_context: dict[str, Any] = {}
    config.set_citations(html_context)

    assert html_context["documenteer_self_citation_metatags"] is None


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


EXAMPLE_CITATIONS_SELF_WITH_PAGE = """

[project]
title = "Example Guide"

[[project.citations]]
doi = "10.71929/rubin/2570308"
self = true
page = "products/catalogs/object"
"""


def test_citations_self_with_page_rejected() -> None:
    """``self`` says the site is the DOI's landing page and ``page`` names a
    landing page inside the site, so an entry that sets both states two
    landing pages for one DOI.
    """
    with pytest.raises(ConfigError) as exc_info:
        DocumenteerConfig.load(EXAMPLE_CITATIONS_SELF_WITH_PAGE)

    message = str(exc_info.value)
    assert "self = true" in message
    assert "page = 'products/catalogs/object'" in message


EXAMPLE_CITATIONS_PREFERRED_WITH_PAGE = """

[project]
title = "Example Guide"
base_url = "https://example.lsst.io"

[[project.citations]]
doi = "10.71929/rubin/3382539"
label = "Object"
type = "dataset"
page = "products/catalogs/object"
title = "Object catalog"
preferred = true
"""


def test_citations_preferred_with_page_allowed() -> None:
    """``preferred`` and ``page`` are compatible: a site can ask readers to
    cite a work whose landing page is one of its own pages.
    """
    config = DocumenteerConfig.load(EXAMPLE_CITATIONS_PREFERRED_WITH_PAGE)

    preferred = config.preferred_citation
    assert preferred is not None
    assert preferred.label == "Object"
    assert preferred.page == "products/catalogs/object"
    assert preferred.is_self is False


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
cff_preferred = true
"""
"""A site that is the landing page of the work its CITATION.cff prefers.

``cff_preferred = true`` is written out because ``self`` on a preferred
citation is otherwise rejected, and the record has to be the preferred one
here: only a reference carries the reduced-precision ``year`` and ``month``
this exercises, where CFF's top level requires a full ``date-released``.
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


PYDANTIC_FRAME = (
    "validation error for",
    "ConfigRoot",
    "Value error,",
    "input_value",
    "input_type",
    "errors.pydantic.dev",
)
"""Fragments of pydantic's own rendering of a `ValidationError`.

The model is Documenteer's implementation detail, so none of these belong in
front of an author who wrote a documenteer.toml.
"""


EXAMPLE_CITATIONS_BAD_DATE = """

[project]
title = "Example Guide"

[[project.citations]]
doi = "10.71929/rubin/3382539"
title = "Object catalog"

[[project.citations]]
doi = "10.71929/rubin/3382540"
label = "Dataset"
title = "Source catalog"
date = "2025-06-00"
"""


def test_config_error_addresses_the_field_that_failed() -> None:
    """A field rejected by a validator is addressed in the vocabulary of
    documenteer.toml, and reported with the validator's own sentence rather
    than through pydantic's frame.
    """
    with pytest.raises(ConfigError) as exc_info:
        DocumenteerConfig.load(EXAMPLE_CITATIONS_BAD_DATE)

    message = str(exc_info.value)
    assert "documenteer.toml" in message
    assert "[[project.citations]] entry #2, field date" in message
    assert "The citation date '2025-06-00' is not a date." in message
    for fragment in PYDANTIC_FRAME:
        assert fragment not in message


EXAMPLE_CITATIONS_LABELLED_SELF_WITH_PAGE = """

[project]
title = "Example Guide"

[[project.citations]]
doi = "10.71929/rubin/3382539"
label = "Object"
title = "Object catalog"
self = true
page = "products/catalogs/object"
"""


def test_config_error_addresses_an_entry_by_its_label() -> None:
    """An error about a whole ``[[project.citations]]`` entry names the entry
    the way the rest of the loader does: by position, with its label.
    """
    with pytest.raises(ConfigError) as exc_info:
        DocumenteerConfig.load(EXAMPLE_CITATIONS_LABELLED_SELF_WITH_PAGE)

    message = str(exc_info.value)
    assert "[[project.citations]] entry #1 (label 'Object')" in message
    assert "sets both self = true" in message
    for fragment in PYDANTIC_FRAME:
        assert fragment not in message


EXAMPLE_CITATIONS_AUTHOR_WITHOUT_A_NAME = """

[project]
title = "Example Guide"

[[project.citations]]
doi = "10.71929/rubin/3382539"
title = "Object catalog"
authors = [{given_name = "Jane"}]
"""


def test_config_error_addresses_a_nested_array() -> None:
    """An array inside an array of tables is addressed by both positions,
    each counted from one and named for what it holds.
    """
    with pytest.raises(ConfigError) as exc_info:
        DocumenteerConfig.load(EXAMPLE_CITATIONS_AUTHOR_WITHOUT_A_NAME)

    message = str(exc_info.value)
    assert "[[project.citations]] entry #1, author #1" in message
    assert "A citation author has no name." in message


EXAMPLE_TITLE_IS_NOT_A_STRING = """

[project]
title = 3
"""


def test_config_error_reports_a_type_error() -> None:
    """A value pydantic rejects on its own — rather than one of the loader's
    validators — is reported with pydantic's own sentence, under an address
    written in the file's vocabulary.
    """
    with pytest.raises(ConfigError) as exc_info:
        DocumenteerConfig.load(EXAMPLE_TITLE_IS_NOT_A_STRING)

    message = str(exc_info.value)
    assert "[project] title" in message
    assert "Input should be a valid string" in message
    for fragment in PYDANTIC_FRAME:
        assert fragment not in message


EXAMPLE_TWO_PROBLEMS = """

[project]
title = 3

[[project.citations]]
doi = "10.71929/rubin/3382539"
title = "Object catalog"
date = "2025-06-00"
"""


def test_config_error_numbers_several_problems() -> None:
    """A file with more than one problem reports them all at once, numbered
    and counted, so the author fixes them in one pass rather than one build
    each.
    """
    with pytest.raises(ConfigError) as exc_info:
        DocumenteerConfig.load(EXAMPLE_TWO_PROBLEMS)

    message = str(exc_info.value)
    assert message.startswith("2 configuration errors in documenteer.toml:")
    assert "1. [project] title" in message
    assert "2. [[project.citations]] entry #1, field date" in message
    assert "Input should be a valid string" in message
    assert "is not a date" in message


def test_config_error_reports_a_toml_syntax_error() -> None:
    """A file TOML itself cannot parse is reported as a configuration error
    naming the file and the place the parser stopped, rather than escaping as
    the parser's own exception.
    """
    with pytest.raises(ConfigError) as exc_info:
        DocumenteerConfig.load("[project\ntitle = 'Example Guide'\n")

    message = str(exc_info.value)
    assert "documenteer.toml" in message
    assert "line 1" in message


def test_config_error_chains_the_validation_error() -> None:
    """The pydantic exception stays chained to the configuration error, so
    the traceback Sphinx saves still has everything needed to debug the model
    itself.
    """
    with pytest.raises(ConfigError) as exc_info:
        DocumenteerConfig.load(EXAMPLE_CITATIONS_BAD_DATE)

    assert isinstance(exc_info.value.__cause__, ValidationError)


def test_config_error_names_no_model_when_a_table_is_not_one() -> None:
    """A table written as something other than a table is reported in TOML's
    vocabulary, since the model standing behind the table is not what the
    author wrote and not what they can fix.
    """
    with pytest.raises(ConfigError) as exc_info:
        DocumenteerConfig.load("project = 3\n")

    message = str(exc_info.value)
    assert "[project]" in message
    assert "should be a table" in message
    assert "ProjectModel" not in message
