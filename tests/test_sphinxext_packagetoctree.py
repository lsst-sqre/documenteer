"""Tests for documenteer.sphinext.packagetoctree (package-toctree and
module-toctree directives).
"""

from documenteer.sphinxext.packagetoctree import _filter_index_pages


def test_filter_index_pages():
    """Test _filter_index_pages."""
    docnames = [
        "index",
        "basedir/A/index",
        "basedir/B/index",
        "basedir/B/subdir/index" "otherdir/C/index",
    ]
    expected = [
        "basedir/A/index",
        "basedir/B/index",
    ]
    assert set(expected) == set(list(_filter_index_pages(docnames, "basedir")))
