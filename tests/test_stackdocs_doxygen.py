"""Tests for the documenteer.stackdocs.doxygen module.
"""

from pathlib import Path

from documenteer.stackdocs.doxygen import (
    DoxygenConfiguration,
    get_cpp_reference_tagfile_path,
    get_doxygen_default_conf_path,
    preprocess_package_doxygen_conf,
)
from documenteer.stackdocs.pkgdiscovery import find_package_docs


def test_default_doxygenconfiguration():
    """Test rendering a DoxygenConfiguration from defaults."""
    doxygenconf = DoxygenConfiguration()
    rendered = doxygenconf.render()

    assert "GENERATE_HTML = YES" in rendered


def test_bool_tag():
    """Test rendering boolean tags in a DoxygenConfiguration."""
    doxygenconf = DoxygenConfiguration()
    lines = []
    doxygenconf._render_bool(lines, "GENERATE_XML", True)
    doxygenconf._render_bool(lines, "GENERATE_XML", False)
    assert lines[0] == "GENERATE_XML = YES"
    assert lines[1] == "GENERATE_XML = NO"


def test_path_tag():
    """Test rendering a path configuration."""
    p = Path(__file__).parent / "xml"
    doxygenconf = DoxygenConfiguration()
    lines = []
    doxygenconf._render_path(lines, "XML_OUTPUT", p)
    assert lines[0] == f"XML_OUTPUT = {p.resolve()}"


def test_path_list_tag():
    """Test rendering a path list configuration."""
    paths = [Path(__file__).parent / "a", Path(__file__).parent / "b"]
    doxygenconf = DoxygenConfiguration()
    lines = []
    doxygenconf._render_path_list(lines, "INPUT", paths)
    assert lines[0] == f"INPUT = {paths[0].resolve()}"
    assert lines[1] == f"INPUT += {paths[1].resolve()}"


def test_str_list_tag():
    """Test rendering a string list configuration."""
    value = [".h", ".cc"]
    doxygenconf = DoxygenConfiguration()
    lines = []
    doxygenconf._render_str_list(lines, "FILE_PATTERNS", value)
    assert lines[0] == f"FILE_PATTERNS = {value[0]}"
    assert lines[1] == f"FILE_PATTERNS += {value[1]}"


def test_inplace_append_config():
    """Test += operation on two configurations."""
    config_a = DoxygenConfiguration(generate_html=True)

    config_b = DoxygenConfiguration(inputs=[Path(__file__).parent])

    config_a += config_b

    assert config_a.generate_html is True
    assert len(config_a.inputs) == 1


def test_add_config():
    """Test + operation on two configurations."""
    config_a = DoxygenConfiguration(generate_html=True)

    config_b = DoxygenConfiguration(inputs=[Path(__file__).parent])

    config = config_a + config_b

    assert config.generate_html is True
    assert len(config.inputs) == 1

    # file_patterns should stay the same, not grow
    assert len(config.file_patterns) == len(config_a.file_patterns)


def test_parse_doxygen_conf():
    conf_path = Path(__file__).parent / "data" / "afw.doxygen.conf"
    conf_text = conf_path.read_text()

    root = conf_path.parent

    conf = DoxygenConfiguration.from_doxygen_conf(conf_text, root)

    assert conf.inputs == [
        Path(
            "/Users/square/j/ws/release/tarball/ad013b8585/build/stack/minicon"
            "da3-4.7.10-4d7b902/EupsBuildDir/DarwinX86/afw-19.0.0-2-g1c703f9ef"
            "+1/afw-19.0.0-2-g1c703f9ef+1/doc"
        ),
        Path(
            "/Users/square/j/ws/release/tarball/ad013b8585/build/stack/minicon"
            "da3-4.7.10-4d7b902/EupsBuildDir/DarwinX86/afw-19.0.0-2-g1c703f9ef"
            "+1/afw-19.0.0-2-g1c703f9ef+1/include"
        ),
        Path(
            "/Users/square/j/ws/release/tarball/ad013b8585/build/stack/minicon"
            "da3-4.7.10-4d7b902/EupsBuildDir/DarwinX86/afw-19.0.0-2-g1c703f9ef"
            "+1/afw-19.0.0-2-g1c703f9ef+1/python"
        ),
        Path(
            "/Users/square/j/ws/release/tarball/ad013b8585/build/stack/minicon"
            "da3-4.7.10-4d7b902/EupsBuildDir/DarwinX86/afw-19.0.0-2-g1c703f9ef"
            "+1/afw-19.0.0-2-g1c703f9ef+1/src"
        ),
        root.joinpath(Path("examples/imageDisplay.ipynb")),
    ]

    assert conf.excludes == [
        root.joinpath(Path("include/lsst/afw/detection/FootprintArray.cc")),
        root.joinpath(Path("include/lsst/afw/detection/detail/dgPsf.cc")),
    ]

    assert conf.generate_xml is True

    assert "*/afw/src/*/*.cc" in conf.exclude_patterns


def test_preprocess_package_doxygen_conf():
    """Test the preprocess_package_doxygen_conf function using
    tests/data/package_alpha.
    """
    package = find_package_docs(
        package_dir=Path(__file__).parent / "data" / "package_alpha"
    )
    conf_text = package.doxygen_conf_in_path.read_text()
    conf = DoxygenConfiguration.from_doxygen_conf(conf_text, package.root_dir)
    preprocess_package_doxygen_conf(conf=conf, package=package)
    expected_include_dir = package.root_dir / "include"

    assert expected_include_dir in conf.inputs


def test_get_doxygen_default_conf_path() -> None:
    """Test get_doxygen_default_conf_path."""
    p = get_doxygen_default_conf_path()
    assert p.exists()
    assert p.is_file()


def test_get_cpp_reference_tagfile_path() -> None:
    """Test get_cpp_reference_tagfile_path."""
    p = get_cpp_reference_tagfile_path()
    assert p.exists()
    assert p.is_file()


def test_include_path() -> None:
    """Test the ``@INCLUDE_PATH`` configuration tag on rendering."""
    config = DoxygenConfiguration(
        include_paths=[get_doxygen_default_conf_path()]
    )
    conf = config.render()

    assert "@INCLUDE_PATH" in conf
    assert "@INCLUDE = doxygen.defaults.conf" in conf
