"""Tests for the documenteer.stackdocs.doxygen module.
"""

from pathlib import Path

from documenteer.stackdocs.doxygen import DoxygenConfiguration


def test_default_doxygenconfiguration():
    """Test rendering a DoxygenConfiguration from defaults.
    """
    doxygenconf = DoxygenConfiguration()
    rendered = doxygenconf.render()

    assert 'GENERATE_XML = YES' in rendered


def test_bool_tag():
    """Test rendering boolean tags in a DoxygenConfiguration.
    """
    doxygenconf = DoxygenConfiguration()
    lines = []
    doxygenconf._render_bool(lines, 'GENERATE_XML', True)
    doxygenconf._render_bool(lines, 'GENERATE_XML', False)
    assert lines[0] == 'GENERATE_XML = YES'
    assert lines[1] == 'GENERATE_XML = NO'


def test_path_tag():
    """Test rendering a path configuration.
    """
    p = Path(__file__).parent / 'xml'
    doxygenconf = DoxygenConfiguration()
    lines = []
    doxygenconf._render_path(lines, 'XML_OUTPUT', p)
    assert lines[0] == f'XML_OUTPUT = {p.resolve()}'


def test_path_list_tag():
    """Test rendering a path list configuration.
    """
    paths = [Path(__file__).parent / 'a', Path(__file__).parent / 'b']
    doxygenconf = DoxygenConfiguration()
    lines = []
    doxygenconf._render_path_list(lines, 'INPUT', paths)
    assert lines[0] == f'INPUT = {paths[0].resolve()}'
    assert lines[1] == f'INPUT += {paths[1].resolve()}'


def test_str_list_tag():
    """Test rendering a string list configuration.
    """
    value = ['.h', '.cc']
    doxygenconf = DoxygenConfiguration()
    lines = []
    doxygenconf._render_str_list(lines, 'FILE_PATTERNS', value)
    assert lines[0] == f'FILE_PATTERNS = {value[0]}'
    assert lines[1] == f'FILE_PATTERNS += {value[1]}'


def test_inplace_append_config():
    """Test += operation on two configurations.
    """
    config_a = DoxygenConfiguration(
        generate_html=True
    )

    config_b = DoxygenConfiguration(
        inputs=[Path(__file__).parent]
    )

    config_a += config_b

    assert config_a.generate_html is True
    assert len(config_a.inputs) == 1


def test_add_config():
    """Test + operation on two configurations.
    """
    config_a = DoxygenConfiguration(
        generate_html=True
    )

    config_b = DoxygenConfiguration(
        inputs=[Path(__file__).parent]
    )

    config = config_a + config_b

    assert config.generate_html is True
    assert len(config.inputs) == 1
