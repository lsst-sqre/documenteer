"""Tests for the ``documenteer.sphinxext.subtasks`` module and
``lsst-subtasks`` directive in particular.
"""

import pytest

from documenteer.sphinxext.subtasks import (
    get_task_config_class, get_subtask_fields)

# Need the LSST Science Pipelines installed for these tests
pytest.importorskip('lsst.pex.config')


def test_get_task_config_class():
    from lsst.pipe.tasks.processCcd import ProcessCcdConfig
    task_name = 'lsst.pipe.tasks.processCcd.ProcessCcdTask'
    config_class = get_task_config_class(task_name)
    print(config_class)
    assert config_class == ProcessCcdConfig


def test_get_subtask_fields():
    """Test get_subtask_fields() using ProcessCcdConfig.
    """
    from lsst.pipe.tasks.processCcd import ProcessCcdConfig
    from lsst.pex.config import ConfigurableField

    subtask_fields = get_subtask_fields(ProcessCcdConfig)
    for subtask_name, subtask in subtask_fields.items():
        print(subtask_name, subtask)
        assert isinstance(subtask_name, str)
        assert isinstance(subtask, ConfigurableField)
