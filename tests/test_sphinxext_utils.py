"""Tests for the ``documenteer.sphinxext.util`` module.
"""

from documenteer.sphinxext.utils import split_role_content


def test_parse_plain_role():
    parts = split_role_content("lsst.afw.table.Table")
    assert parts["last_component"] is False
    assert parts["display"] is None
    assert parts["ref"] == "lsst.afw.table.Table"


def test_parse_shortened_role():
    parts = split_role_content("~lsst.afw.table.Table")
    assert parts["last_component"] is True
    assert parts["display"] is None
    assert parts["ref"] == "lsst.afw.table.Table"


def test_parse_display_role():
    parts = split_role_content("Table <lsst.afw.table.Table>")
    assert parts["last_component"] is False
    assert parts["display"] == "Table"
    assert parts["ref"] == "lsst.afw.table.Table"
