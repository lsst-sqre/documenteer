"""JIRA ticket reference roles (for stories, epics, RFCs, etc.).

This module is heavily influenced by sphinx-issue (Steven Loria). See
/licenses/sphinx-issue.txt for licensing information.
"""

import logging

from docutils import nodes, utils

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def _make_ticket_node(ticket_id, config, options=None):
    """Construct a reference node for a JIRA ticket."""
    options = options or {}
    ref = config.jira_uri_template.format(ticket=ticket_id)
    link = nodes.reference(text=ticket_id, refuri=ref, **options)
    return link


def _comma_separator(i, length):
    """A separator for an entirely comma-separated list given current item
    index `i` and total list length `length`. `None` if there should be
    no separator (last item).
    """
    if length == 1:
        return None
    elif i != length - 1:
        return ", "
    else:
        return None


def _oxford_comma_separator(i, length):
    """Make a separator for a prose-like list with `,` between items except
    for `, and` after the second to last item.
    """
    if length == 1:
        return None
    elif length < 3 and i == 0:
        return " and "
    elif i < length - 2:
        return ", "
    elif i == length - 2:
        return ", and "
    else:
        return None


def jira_role(
    name,
    rawtext,
    text,
    lineno,
    inliner,
    options=None,
    content=None,
    oxford_comma=True,
):
    """Sphinx role for referencing a JIRA ticket.

    Examples::

        :jira:`DM-6181` -> DM-6181
        :jira:`DM-6181,DM-6181` -> DM-6180 and DM-6181
        :jira:`DM-6181,DM-6181,DM-6182` -> DM-6180, DM-6181, and DM-6182
    """
    options = options or {}
    content = content or []
    config = inliner.document.settings.env.app.config

    ticket_ids = [each.strip() for each in utils.unescape(text).split(",")]
    n_tickets = len(ticket_ids)

    if oxford_comma:
        sep_factory = _oxford_comma_separator
    else:
        sep_factory = _comma_separator

    node_list = []
    for i, ticket_id in enumerate(ticket_ids):
        node = _make_ticket_node(ticket_id, config, options=options)
        node_list.append(node)
        sep_text = sep_factory(i, n_tickets)
        if sep_text is not None:
            sep = nodes.raw(text=sep_text, format="html")
            node_list.append(sep)
    return node_list, []


def jira_bracket_role(
    name,
    rawtext,
    text,
    lineno,
    inliner,
    options=None,
    content=None,
    open_symbol="[",
    close_symbol="]",
):
    """Sphinx role for referencing a JIRA ticket with ticket numbers
    enclosed in braces. Useful for changelogs.

    Examples::

        :jirab:`DM-6181` -> [DM-6181]
        :jirab:`DM-6181,DM-6181` -> [DM-6180, DM-6181]
        :jirab:`DM-6181,DM-6181,DM-6182` -> [DM-6180, DM-6181, DM-6182]
    """
    node_list, _ = jira_role(
        name,
        rawtext,
        text,
        lineno,
        inliner,
        options=options,
        content=None,
        oxford_comma=False,
    )
    node_list.insert(0, nodes.raw(text=open_symbol, format="html"))
    node_list.append(nodes.raw(text=close_symbol, format="html"))
    return node_list, []


def jira_parens_role(
    name, rawtext, text, lineno, inliner, options=None, content=None
):
    """Sphinx role for referencing a JIRA ticket with ticket numbers
    enclosed in parentheses. Useful for changelogs.

    Examples::

        :jirap:`DM-6181` -> (DM-6181)
        :jirap:`DM-6181,DM-6181` -> (DM-6180, DM-6181)
        :jirap:`DM-6181,DM-6181,DM-6182` -> (DM-6180, DM-6181, DM-6182)
    """
    return jira_bracket_role(
        name,
        rawtext,
        text,
        lineno,
        inliner,
        options=None,
        content=None,
        open_symbol="(",
        close_symbol=")",
    )


def setup(app):
    app.add_config_value(
        "jira_uri_template",
        default="https://jira.lsstcorp.org/browse/{ticket}",
        rebuild="html",
    )
    app.add_role("jira", jira_role)
    app.add_role("jirab", jira_bracket_role)
    app.add_role("jirap", jira_parens_role)
