from setuptools import setup, find_packages
import os


PACKAGENAME = 'documenteer'
DESCRIPTION = 'Tools for LSST DM documentation projects'
AUTHOR = 'Jonathan Sick'
AUTHOR_EMAIL = 'jsick@lsst.org'
LICENSE = 'MIT'
URL = 'https://github.com/lsst-sqre/documenteer'
VERSION = '0.1.0'


def read(filename):
    full_filename = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        filename)
    return open(full_filename).read()

long_description = read('README.rst')


setup(
    name=PACKAGENAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=long_description,
    url=URL,
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    license=LICENSE,
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    keywords='sphinx documentation lsst',
    packages=find_packages(exclude=['docs', 'tests*']),
    install_requires=['future', 'sphinx', 'tox', 'PyYAML', 'sphinx-prompt'],
    tests_require=['nose', 'tox'],
    # package_data={},
)
