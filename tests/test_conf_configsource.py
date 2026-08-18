"""Tests for the documenteer.conf._configsource module."""

from __future__ import annotations

from pathlib import Path

import pytest

from documenteer.conf._configsource import ConfigSource, detect_config_source


def test_detects_guide(tmp_path: Path) -> None:
    """A ``documenteer.toml`` beside ``conf.py`` marks a user guide."""
    (tmp_path / "conf.py").write_text("")
    (tmp_path / "documenteer.toml").write_text("")

    assert detect_config_source(tmp_path) is ConfigSource.GUIDE


def test_detects_technote(tmp_path: Path) -> None:
    """A ``technote.toml`` beside ``conf.py`` marks a technote."""
    (tmp_path / "conf.py").write_text("")
    (tmp_path / "technote.toml").write_text("")

    assert detect_config_source(tmp_path) is ConfigSource.TECHNOTE


def test_detects_neither(tmp_path: Path) -> None:
    """Without either configuration file the Sphinx configuration came
    from ``conf.py`` directly, which is neither project type.
    """
    (tmp_path / "conf.py").write_text("")

    assert detect_config_source(tmp_path) is ConfigSource.UNKNOWN


def test_technote_wins_when_both_present(tmp_path: Path) -> None:
    """When both configuration files somehow exist, ``technote.toml``
    wins — the precedence is specified, not incidental.
    """
    (tmp_path / "conf.py").write_text("")
    (tmp_path / "documenteer.toml").write_text("")
    (tmp_path / "technote.toml").write_text("")

    assert detect_config_source(tmp_path) is ConfigSource.TECHNOTE


def test_missing_directory(tmp_path: Path) -> None:
    """A directory that does not exist yields UNKNOWN rather than
    raising: a helper whose only job is to word a message must never be
    able to fail a build.
    """
    assert detect_config_source(tmp_path / "nope") is ConfigSource.UNKNOWN


def test_unreadable_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An OSError while probing the directory yields UNKNOWN rather than
    propagating.
    """

    def _raise(self: Path) -> bool:
        raise PermissionError(self)

    monkeypatch.setattr(Path, "is_file", _raise)

    assert detect_config_source(tmp_path) is ConfigSource.UNKNOWN


def test_accepts_str_path(tmp_path: Path) -> None:
    """The confdir may be given as a string as well as a Path."""
    (tmp_path / "technote.toml").write_text("")

    assert detect_config_source(str(tmp_path)) is ConfigSource.TECHNOTE
