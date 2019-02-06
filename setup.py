from setuptools import setup, find_packages

import os


packagename = 'documenteer'
description = 'Tools for LSST DM documentation projects'
author = 'Association of Universities for Research in Astronomy, Inc.'
author_email = 'sqre-admin@lists.lsst.org'
license = 'MIT'
url = 'https://github.com/lsst-sqre/documenteer'
classifiers = [
    'Development Status :: 4 - Beta',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
]
keywords = 'sphinx documentation lsst'


def read(filename):
    full_filename = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        filename)
    return open(full_filename).read()


long_description = read('README.rst')


# Core dependencies
install_requires = [
    'Sphinx>=1.7.0,<1.8.0',
    'PyYAML',
    'sphinx-prompt',
    'GitPython',
    'requests',
    'click>=6.7,<7.0'
]

# Project-specific dependencies
extras_require = {
    # For technical note Sphinx projects
    'technote': [
        'lsst-dd-rtd-theme==0.2.1',
        # 0.4.1 is incompatible with Sphinx <1.8.0. Unpin once we upgrade
        # Sphinx.
        'sphinxcontrib-bibtex==0.4.0'
    ],

    # For the pipelines.lsst.io documentation project
    'pipelines': [
        'lsst-sphinx-bootstrap-theme>=0.2.0,<0.3.0',
        'numpydoc>=0.8.0,<0.9.0',
        'sphinx-automodapi>=0.7,<0.8',
        'breathe==4.4.0',
        'sphinx-jinja==1.1.0',
    ],

    # For documenteer development environments
    'dev': [
        'wheel>=0.29.0',
        'twine>=1.8.1',
        'pytest==3.0.4',
        'pytest-cov==2.4.0',
        'pytest-flake8==0.8.1',
        'pytest-mock==1.4.0',
        'flake8==3.3.0',
        # Extensions for documenteer's own docs. Perhaps add this to main
        # installation for other projects?
        'sphinx-click>=1.2.0,<1.3.0',
    ],
}
# Add project dependencies to the dev dependencies
extras_require['dev'].extend(extras_require['technote'])
extras_require['dev'].extend(extras_require['pipelines'])

# Dependencies for tests_require (python setup.py test)
tests_require = extras_require['dev']

setup_requires = [
    'setuptools_scm',
    'pytest-runner>=2.11.1,<3',
]

console_scripts = [
    'stack-docs = documenteer.stackdocs.stackcli:main',
    'package-docs = documenteer.stackdocs.packagecli:main',
    'build-stack-docs = documenteer.stackdocs.build:run_build_cli',
    'refresh-lsst-bib = documenteer.bin.refreshlsstbib:run'
]


setup(
    name=packagename,
    description=description,
    long_description=long_description,
    url=url,
    author=author,
    author_email=author_email,
    license=license,
    classifiers=classifiers,
    keywords=keywords,
    packages=find_packages(exclude=['docs', 'tests*']),
    install_requires=install_requires,
    setup_requires=setup_requires,
    tests_require=tests_require,
    extras_require=extras_require,
    entry_points={'console_scripts': console_scripts},
    use_scm_version=True,
)
