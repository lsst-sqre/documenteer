from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import pytest

from documenteer.sphinxconfig.utils import form_ltd_edition_name


@pytest.mark.parametrize("git_ref,name", [
    ('master', 'Current'),
    ('tickets/DM-6120', 'DM-6120'),
    ('v1.2.3', 'v1.2.3'),
    ('draft/v1.2.3', 'draft-v1-2-3'),
])
def test_form_ltd_edition_name(git_ref, name):
    assert name == form_ltd_edition_name(git_ref_name=git_ref)
