from setuptools import setup, find_packages
import os


packagename = 'documenteer'
description = 'Tools for LSST DM documentation projects'
author = 'Jonathan Sick'
author_email = 'jsick@lsst.org'
license = 'MIT'
url = 'https://github.com/lsst-sqre/documenteer'
version = '0.1.1'


def read(filename):
    full_filename = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        filename)
    return open(full_filename).read()

long_description = read('README.rst')


setup(
    name=packagename,
    version=version,
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
    install_requires=['future', 'sphinx', 'tox', 'PyYAML', 'sphinx-prompt'],
    tests_require=['nose', 'tox'],
    # package_data={},
)
