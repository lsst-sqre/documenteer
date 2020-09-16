"""LSST DocuShare/ls.st reference roles."""

from docutils import nodes


def lsst_doc_shortlink_role(
    name, rawtext, text, lineno, inliner, options=None, content=None
):
    """Link to LSST documents given their handle using LSST's ls.st link
    shortener.

    Example::

        :ldm:`151`
    """
    options = options or {}
    content = content or []
    node = nodes.reference(
        text="{0}-{1}".format(name.upper(), text),
        refuri="https://ls.st/{0}-{1}".format(name, text),
        **options,
    )
    return [node], []


def lsst_doc_shortlink_titlecase_display_role(
    name, rawtext, text, lineno, inliner, options=None, content=None
):
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
        text="{0}-{1}".format(name.title(), text),
        refuri="https://ls.st/{0}-{1}".format(name, text),
        **options,
    )
    return [node], []


def setup(app):
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
    # LSST SQuaRE Technical Note
    app.add_role("sqr", lsst_doc_shortlink_role)
    # LSST Data Management Technical Note
    app.add_role("dmtn", lsst_doc_shortlink_role)
    # LSST Simulations Technical Note
    app.add_role("smtn", lsst_doc_shortlink_role)
