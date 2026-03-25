"""Tests for the Commander serial interface."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from sentry.commander import Commander


@pytest.fixture()
def mock_serial() -> Generator[MagicMock, None, None]:
    """Returns a mock serial.Serial instance."""
    with patch("sentry.commander.serial.Serial") as mock_cls:
        instance = mock_cls.return_value
        instance.is_open = True
        yield instance


def test_fire_sends_correct_bytes(mock_serial: MagicMock) -> None:
    with Commander(port="/dev/ttyACM0") as cmd:
        cmd.fire()
    calls = [call.args[0] for call in mock_serial.write.call_args_list]
    assert b"F\n" in calls


def test_safe_sends_correct_bytes(mock_serial: MagicMock) -> None:
    with Commander(port="/dev/ttyACM0") as cmd:
        cmd.safe()
    calls = [call.args[0] for call in mock_serial.write.call_args_list]
    assert b"S\n" in calls


def test_close_sends_safe_first(mock_serial: MagicMock) -> None:
    with Commander(port="/dev/ttyACM0"):
        pass  # __exit__ calls close()
    first_write = mock_serial.write.call_args_list[0].args[0]
    assert first_write == b"S\n"


def test_pan_sends_correct_bytes(mock_serial: MagicMock) -> None:
    with Commander(port="/dev/ttyACM0") as cmd:
        cmd.pan(90)
    calls = [call.args[0] for call in mock_serial.write.call_args_list]
    assert b"P90\n" in calls


def test_tilt_sends_correct_bytes(mock_serial: MagicMock) -> None:
    with Commander(port="/dev/ttyACM0") as cmd:
        cmd.tilt(45)
    calls = [call.args[0] for call in mock_serial.write.call_args_list]
    assert b"T45\n" in calls


def test_pan_clamps_to_max(mock_serial: MagicMock) -> None:
    with Commander(port="/dev/ttyACM0") as cmd:
        cmd.pan(999)
    calls = [call.args[0] for call in mock_serial.write.call_args_list]
    assert b"P359\n" in calls


def test_tilt_clamps_to_max(mock_serial: MagicMock) -> None:
    with Commander(port="/dev/ttyACM0") as cmd:
        cmd.tilt(999)
    calls = [call.args[0] for call in mock_serial.write.call_args_list]
    assert b"T270\n" in calls
