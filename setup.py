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
    'Sphinx>=1.5.1',
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
        'lsst-sphinx-bootstrap-theme>=0.1.0',
        'astropy-helpers>=0.2.0',
        'breathe==4.4.0'
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
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    keywords='sphinx documentation lsst',
    packages=find_packages(exclude=['docs', 'tests*']),
    install_requires=install_requires,
    extras_require=extras_require,
)
