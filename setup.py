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
    'future',
    'docutils==0.13.1',  # currently pinned in conjunction with Sphinx
    'Sphinx>=1.5.0,<1.6.0',
    'PyYAML',
    'sphinx-prompt',
    'GitPython'
]


# Project-specific dependencies
extras_require = {
    # For technical note Sphinx projects
    'technote': [
        'lsst-dd-rtd-theme==0.1.0',
        'sphinxcontrib-bibtex'
    ],

    # For the pipelines.lsst.io documentation project
    'pipelines': [
        'lsst-sphinx-bootstrap-theme>=0.1.0,<0.2.0',
        'astropy-helpers>=1.2.0,<1.4.0',
        'breathe==4.4.0'
    ],

    # For documenteer development environments
    'dev': [
        'wheel>=0.29.0',
        'twine>=1.8.1',
        'pytest==3.0.4',
        'pytest-cov==2.4.0',
        'pytest-flake8==0.8.1',
        'pytest-mock==1.4.0'
    ]
}


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
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='sphinx documentation lsst',
    packages=find_packages(exclude=['docs', 'tests*']),
    install_requires=install_requires,
    extras_require=extras_require,
    entry_points={
        'console_scripts': [
            'build-stack-docs = documenteer.stackdocs.build:run_build_cli'
        ]
    },
)
