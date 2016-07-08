"""Tests for documenteer.designdocs.ddconfig"""

from datetime import datetime
import pytest

from documenteer.designdocs.ddconfig import _build_confs


@pytest.fixture()
def sample_metadata():
    m = {'series': 'SQR',
         'serial_number': '000',
         'doc_id': 'SQR-000',
         'doc_title': 'The Title',
         'authors': ['Jonathan Sick'],
         'last_revised': '2015-11-23',
         'version': '1.0.0',
         'copyright': '2016 AURA/LSST',
         'description': 'Description',
         'url': 'https://repo.example.org',
         'docushare_url': None,
         'github_url': 'https://example.org/org/repo'}
    return m


@pytest.mark.parametrize(
    'branch_name', ['master', 'tickets/DM-0000'])
def test_git_version(mocker, sample_metadata, branch_name):
    import documenteer.designdocs.ddconfig
    documenteer.designdocs.ddconfig.read_git_branch = mocker.MagicMock()
    documenteer.designdocs.ddconfig.read_git_branch.return_value = branch_name

    sample_metadata.pop('version')

    config = _build_confs(sample_metadata)

    assert config['version'] == branch_name


@pytest.mark.parametrize(
    'input,expected',
    [(datetime(2016, 7, 1), '2016-07-01')])
def test_git_last_revised(mocker, sample_metadata, input, expected):
    import documenteer.designdocs.ddconfig
    documenteer.designdocs.ddconfig.read_git_commit_timestamp \
        = mocker.MagicMock()
    documenteer.designdocs.ddconfig.read_git_commit_timestamp.return_value \
        = input

    sample_metadata.pop('last_revised')

    config = _build_confs(sample_metadata)

    assert config['today'] == expected
    assert config['html_context']['last_revised'] == expected


def test_hard_coded_version(sample_metadata):
    config = _build_confs(sample_metadata)
    assert config['version'] == sample_metadata['version']


def test_hard_coded_last_revised(sample_metadata):
    config = _build_confs(sample_metadata)
    assert config['html_context']['last_revised'] \
        == sample_metadata['last_revised']
