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
    writes = [call.args[0] for call in mock_serial.write.call_args_list]
    assert b"S\n" in writes
    # SAFE must come after all servo movement
    safe_idx = next(i for i, w in enumerate(writes) if w == b"S\n")
    assert all(
        i <= safe_idx for i, w in enumerate(writes) if w.startswith(b"P") or w.startswith(b"T")
    )


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
    assert b"P180\n" in calls


def test_tilt_clamps_to_max(mock_serial: MagicMock) -> None:
    with Commander(port="/dev/ttyACM0") as cmd:
        cmd.tilt(999)
    calls = [call.args[0] for call in mock_serial.write.call_args_list]
    assert b"T180\n" in calls


def test_slew_to_steps_incrementally(mock_serial: MagicMock) -> None:
    with Commander(port="/dev/ttyACM0") as cmd:
        cmd._pan = 90
        cmd._tilt = 90
        mock_serial.write.reset_mock()  # ignore __enter__ writes
        cmd.slew_to(96, 96)
        writes = [call.args[0] for call in mock_serial.write.call_args_list]
    # Should have stepped: 90→92→94→96, 90→92→94→96
    assert b"P92\n" in writes
    assert b"P94\n" in writes
    assert b"P96\n" in writes
    assert b"T92\n" in writes
    assert b"T94\n" in writes
    assert b"T96\n" in writes


def test_slew_to_already_at_target(mock_serial: MagicMock) -> None:
    with Commander(port="/dev/ttyACM0") as cmd:
        cmd._pan = 180
        cmd._tilt = 90
        mock_serial.write.reset_mock()  # ignore __enter__ writes
        cmd.slew_to(180, 90)
        writes = [call.args[0] for call in mock_serial.write.call_args_list]
    # No pan or tilt writes — already at target
    assert not any(w.startswith(b"P") or w.startswith(b"T") for w in writes)


def test_slew_to_clamps_to_limits(mock_serial: MagicMock) -> None:
    with Commander(port="/dev/ttyACM0") as cmd:
        cmd._pan = 355
        cmd._tilt = 178
        cmd.slew_to(999, 999)
        # Assert inside with block before close() slews back to center
        assert cmd._pan == 180
        assert cmd._tilt == 180
