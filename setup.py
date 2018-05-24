from setuptools import setup, find_packages
import versioneer

import os


packagename = 'documenteer'
description = 'Tools for LSST DM documentation projects'
author = 'Association of Universities for Research in Astronomy, Inc.'
author_email = 'sqre-admin@lists.lsst.org'
license = 'MIT'
url = 'https://github.com/lsst-sqre/documenteer'


def read(filename):
    full_filename = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        filename)
    return open(full_filename).read()


long_description = read('README.rst')


# Core dependencies
install_requires = [
    'docutils==0.13.1',  # currently pinned in conjunction with Sphinx
    'Sphinx>=1.5.0,<1.6.0',
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
        'sphinxcontrib-bibtex'
    ],

    # For the pipelines.lsst.io documentation project
    'pipelines': [
        'lsst-sphinx-bootstrap-theme>=0.2.0,<0.3.0',
        'astropy-helpers>=3.0.0,<4.0.0',
        'breathe==4.4.0'
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
    ],
}

# Dependencies for tests_require (python setup.py test)
tests_require = []
for k in extras_require:
    tests_require += extras_require[k]

setup_requires = [
    'pytest-runner>=2.11.1,<3',
]

setup(
    name=packagename,
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description=description,
    long_description=long_description,
    url=url,
    author=author,
    author_email=author_email,
    license=license,
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='sphinx documentation lsst',
    packages=find_packages(exclude=['docs', 'tests*']),
    install_requires=install_requires,
    setup_requires=setup_requires,
    tests_require=tests_require,
    extras_require=extras_require,
    entry_points={
        'console_scripts': [
            'stack-docs = documenteer.stackdocs.stackcli:main',
            'package-docs = documenteer.stackdocs.packagecli:main',
            'build-stack-docs = documenteer.stackdocs.build:run_build_cli',
            'refresh-lsst-bib = documenteer.bin.refreshlsstbib:run'
        ]
    },
)
