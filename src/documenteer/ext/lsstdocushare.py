"""LSST the Docs and DocuShare/ls.st reference roles."""

from __future__ import annotations

from typing import TYPE_CHECKING

from docutils import nodes

from ..version import __version__

if TYPE_CHECKING:
    from docutils.nodes import Node, system_message
    from docutils.parsers.rst.states import Inliner
    from sphinx.application import Sphinx
    from sphinx.util.typing import ExtensionMetadata


def lsstio_doc_shortlink_role(
    name: str,
    rawtext: str,
    text: str,
    lineno: int,
    inliner: Inliner,
    options: dict | None = None,
    content: list[str] | None = None,
) -> tuple[list[Node], list[system_message]]:
    """Link to LSST documents given their handle that are hosted on
    lsst.io (Rubin's deployment of LSST the Docs).

    Example::

        :sqr:`001`
    """
    options = options or {}
    content = content or []
    node = nodes.reference(
        text=f"{name.upper()}-{text}",
        refuri=f"https://{name.lower()}-{text}.lsst.io/",
        **options,
    )
    return [node], []


def lsst_doc_shortlink_role(
    name: str,
    rawtext: str,
    text: str,
    lineno: int,
    inliner: Inliner,
    options: dict | None = None,
    content: list[str] | None = None,
) -> tuple[list[Node], list[system_message]]:
    """Link to LSST documents given their handle using LSST's ls.st link
    shortener.

    Example::

        :ldm:`151`
    """
    options = options or {}
    content = content or []
    node = nodes.reference(
        text=f"{name.upper()}-{text}",
        refuri=f"https://ls.st/{name}-{text}",
        **options,
    )
    return [node], []


def lsst_doc_shortlink_titlecase_display_role(
    name: str,
    rawtext: str,
    text: str,
    lineno: int,
    inliner: Inliner,
    options: dict | None = None,
    content: list[str] | None = None,
) -> tuple[list[Node], list[system_message]]:
    """Link to LSST documents given their handle using LSST's ls.st link
    shortener with the document handle displayed in title case.

    This role is useful for Document, Report, Minutes, and Collection
    DocuShare handles.

    Example::

        :document:`1`
    """
    options = options or {}
    content = content or []
    node = nodes.reference(
        text=f"{name.title()}-{text}",
        refuri=f"https://ls.st/{name}-{text}",
        **options,
    )
    return [node], []


def setup(app: Sphinx) -> ExtensionMetadata:
    """Set up the LSST DocuShare and ls.st reference roles."""
    # LSST Data Management
    app.add_role("ldm", lsst_doc_shortlink_role)
    # LSST Systems Engineering
    app.add_role("lse", lsst_doc_shortlink_role)
    # LSST Project Management
    app.add_role("lpm", lsst_doc_shortlink_role)
    # LSST Telescope & Site
    app.add_role("lts", lsst_doc_shortlink_role)
    # LSST Education & Public Outreach
    app.add_role("lep", lsst_doc_shortlink_role)
    # LSST Camera System
    app.add_role("lca", lsst_doc_shortlink_role)
    # LSST Board
    app.add_role("lsstc", lsst_doc_shortlink_role)
    # LSST Change Request
    app.add_role("lcr", lsst_doc_shortlink_role)
    # LSST Camera Change Notice
    app.add_role("lcn", lsst_doc_shortlink_role)
    # LSST Operations
    app.add_role("lso", lsst_doc_shortlink_role)
    # LSST Data Management Test Report
    app.add_role("dmtr", lsst_doc_shortlink_role)
    # LSST Document
    app.add_role("document", lsst_doc_shortlink_titlecase_display_role)
    # LSST Report
    app.add_role("report", lsst_doc_shortlink_titlecase_display_role)
    # LSST Minutes
    app.add_role("minutes", lsst_doc_shortlink_titlecase_display_role)
    # DocuShare collection
    app.add_role("collection", lsst_doc_shortlink_titlecase_display_role)

    # Technical notes are hosted canonically on www.lsst.io

    # LSST SQuaRE Technical Note
    app.add_role("sqr", lsstio_doc_shortlink_role)
    # LSST Data Management Technical Note
    app.add_role("dmtn", lsstio_doc_shortlink_role)
    # LSST Simulations Technical Note
    app.add_role("smtn", lsstio_doc_shortlink_role)
    # SITCOMTN Technical Note
    app.add_role("sitcomtn", lsstio_doc_shortlink_role)
    # PST Technical Note
    app.add_role("pstn", lsstio_doc_shortlink_role)
    # Rubin Technical Note
    app.add_role("rtn", lsstio_doc_shortlink_role)
    # IT Technical Note
    app.add_role("ittn", lsstio_doc_shortlink_role)
    # T&S Technical Note
    app.add_role("tstn", lsstio_doc_shortlink_role)

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
