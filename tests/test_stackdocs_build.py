"""Tests for the documenteer.stackdocs.build module (build-stack-docs
executable).
"""

import os

from documenteer.stackdocs import build


def test_find_package_docs():
    package_dir = os.path.join(
        os.path.dirname(__file__),
        'data',
        'package_alpha')
    package_docs = build.find_package_docs(package_dir)

    assert 'package_alpha' in package_docs.package_dirs
    expected_package_dir = os.path.join(package_dir, 'doc', 'package_alpha')
    assert package_docs.package_dirs['package_alpha'] == expected_package_dir

    assert 'package.alpha' in package_docs.module_dirs
    expected_module_dir = os.path.join(package_dir, 'doc', 'package.alpha')
    assert package_docs.module_dirs['package.alpha'] == expected_module_dir

    assert 'package_alpha' in package_docs.static_dirs
    expected_static_dir = os.path.join(package_dir,
                                       'doc',
                                       '_static/package_alpha')
    assert package_docs.static_dirs['package_alpha'] == expected_static_dir
