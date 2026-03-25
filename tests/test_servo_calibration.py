"""Manual servo calibration script for pan (continuous) and tilt (270°).

Run on the Pi with the Arduino + PCA9685 connected:

    pytest tests/test_servo_calibration.py -v -s -m hardware

Each test moves the servo to a specific tick value and pauses so you can
observe the physical position. Edit the TICKS constants at the top of this
file until the positions match your hardware, then copy the final values
into firmware/include/sentry.h.

Pan servo (360° continuous):
    MID  = stop point  (tune first — find exact value where servo halts)
    MIN  = full speed one direction
    MAX  = full speed other direction

Tilt servo (270° positional):
    MIN  = 0°   physical endpoint
    MAX  = 270° physical endpoint
"""

from __future__ import annotations

import time
from collections.abc import Generator

import pytest

from sentry.commander import Commander

PORT = "/dev/ttyACM0"
OBSERVE_S = 3.0  # seconds to hold each position for observation

# ----------------------------------------
# Tune these values and copy finals into sentry.h

PAN_TICKS_MID = 307  # stop point - servo should not move
PAN_TICKS_MIN = 205  # full speed direction A
PAN_TICKS_MAX = 409  # full speed direction B

TILT_TICKS_MIN = 102  # 0 deg.
TILT_TICKS_MAX = 512  # 270 deg.

# ----------------------------------------


@pytest.fixture()
def cmd() -> Generator[Commander, None, None]:
    with Commander(port=PORT) as commander:
        yield commander


# ----------------------------------------
# Pan calibration
# ----------------------------------------


@pytest.mark.hardware
def test_pan_mid_is_stop(cmd: Commander) -> None:
    """Pan servo should be stationary at MID. Tune PAN_TICKS_MID until it stops."""
    print(f"\n -> Sending PAN MID ({PAN_TICKS_MID} ticks) - servo should STOP.")
    cmd._writeline(f"P{_ticks_to_pan_deg(PAN_TICKS_MID)}".encode())
    time.sleep(OBSERVE_S)


@pytest.mark.hardware
def test_pan_min_direction(cmd: Commander) -> None:
    """Pan servo should rotate in direction A at MIN ticks, then stop."""
    print(f"\n -> Sending PAN MIN ({PAN_TICKS_MIN} ticks) - should rotate direction A.")
    cmd._writeline(f"P{_ticks_to_pan_deg(PAN_TICKS_MIN)}".encode())
    time.sleep(OBSERVE_S)
    print(f" -> Stopping (MID = {PAN_TICKS_MID} ticks).")
    cmd._writeline(f"P{_ticks_to_pan_deg(PAN_TICKS_MID)}".encode())
    time.sleep(1.0)


@pytest.mark.hardware
def test_pan_max_direction(cmd: Commander) -> None:
    """Pan servo should rotate in direction B at MAX ticks, then stop."""
    print(f"\n -> Sending PAN MAX ({PAN_TICKS_MAX} ticks) - should rotate direction B.")
    cmd._writeline(f"P{_ticks_to_pan_deg(PAN_TICKS_MAX)}".encode())
    time.sleep(OBSERVE_S)
    print(f" -> Stopping (MID = {PAN_TICKS_MID} ticks).")
    cmd._writeline(f"P{_ticks_to_pan_deg(PAN_TICKS_MID)}".encode())
    time.sleep(1.0)


# ----------------------------------------
# Tilt calibration
# ----------------------------------------


@pytest.mark.hardware
def test_tilt_min_position(cmd: Commander) -> None:
    """Tilt servo should move to 0 deg. physical endpoint."""
    print(f"\n -> Sending TILT MIN ({TILT_TICKS_MIN} ticks) - should be at 0 deg.")
    cmd._writeline(b"T0")
    time.sleep(OBSERVE_S)


@pytest.mark.hardware
def test_tilt_max_position(cmd: Commander) -> None:
    """Tilt servo should move to 270 deg. physical endpoint."""
    print(f"\n -> Sending TILT MAX ({TILT_TICKS_MAX} ticks) - should be at 270 deg.")
    cmd._writeline(b"T270")
    time.sleep(OBSERVE_S)


# ----------------------------------------
# Helpers
# ----------------------------------------


def _ticks_to_pan_deg(ticks: int) -> int:
    """Convert raw PCA9685 ticks to the 0-359 degree value Commander expects.

    The firmware maps 0-359 deg linearly to PAN_TICKS_MIN-MAX, so we invert
    that mapping here to send a specific tick value for calibration purposes.
    """
    from sentry.commander import _PAN_MAX, _PAN_MIN

    deg = round((ticks - PAN_TICKS_MIN) / (PAN_TICKS_MAX - PAN_TICKS_MIN) * (_PAN_MAX - _PAN_MIN))
    return max(_PAN_MIN, min(_PAN_MAX, deg))
