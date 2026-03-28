"""Manual servo calibration script for pan (270°) and tilt (270°/180°).

Run on the Pi with the Arduino + PCA9685 connected:

    pytest tests/test_servo_calibration.py -v -s -m hardware

Each test moves the servo to a specific tick value and pauses so you can
observe the physical position. Edit the TICKS constants at the top of this
file until the positions match your hardware, then copy the final values
into firmware/include/sentry.h.

Pan servo (270° positional):
    MIN  = 0°   physical endpoint
    MAX  = 270° physical endpoint
    MID  = 135° mechanical center (verify this looks centered)

Tilt servo (positional):
    MIN  = 0°   physical endpoint (90° down)
    MAX  = 180° physical endpoint (90° up)
    MID  = 90°  horizontal rest
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

PAN_TICKS_MIN = 102  # 0 deg physical endpoint
PAN_TICKS_MAX = 375  # 270 deg physical endpoint

TILT_TICKS_MIN = 102  # 0 deg (90 deg down)
TILT_TICKS_MAX = 375  # 180 deg (90 deg up)

# ----------------------------------------


@pytest.fixture()
def cmd() -> Generator[Commander, None, None]:
    with Commander(port=PORT) as commander:
        yield commander


# ----------------------------------------
# Pan calibration
# ----------------------------------------


@pytest.mark.hardware
def test_pan_min_position(cmd: Commander) -> None:
    """Pan servo should move to 0 deg physical endpoint."""
    print(f"\n -> Sending PAN MIN ({PAN_TICKS_MIN} ticks) - should be at 0 deg.")
    cmd.pan(0)
    time.sleep(OBSERVE_S)


@pytest.mark.hardware
def test_pan_mid_position(cmd: Commander) -> None:
    """Pan servo should move to 135 deg — mechanical centre."""
    print("\n -> Sending PAN 135 - servo should be centred.")
    cmd.pan(135)
    time.sleep(OBSERVE_S)


@pytest.mark.hardware
def test_pan_max_position(cmd: Commander) -> None:
    """Pan servo should move to 270 deg physical endpoint."""
    print(f"\n -> Sending PAN MAX ({PAN_TICKS_MAX} ticks) - should be at 270 deg.")
    cmd.pan(270)
    time.sleep(OBSERVE_S)


@pytest.mark.hardware
def test_pan_sweep(cmd: Commander) -> None:
    """Sweep pan from 0 to 270 deg in steps to verify linearity."""
    print("\n -> Sweeping pan 0 -> 270 deg in 45 deg steps.")
    for deg in range(0, 271, 45):
        print(f"    PAN {deg} deg")
        cmd.pan(deg)
        time.sleep(1.5)
    cmd.pan(135)  # return to center
    time.sleep(1.0)


# ----------------------------------------
# Tilt calibration
# ----------------------------------------


@pytest.mark.hardware
def test_tilt_min_position(cmd: Commander) -> None:
    """Tilt servo should move to 0 deg physical endpoint (90 deg down)."""
    print(f"\n -> Sending TILT MIN ({TILT_TICKS_MIN} ticks) - should be 90 deg down.")
    cmd.tilt(0)
    time.sleep(OBSERVE_S)


@pytest.mark.hardware
def test_tilt_horizontal_rest(cmd: Commander) -> None:
    """Tilt servo should move to horizontal rest position at 90 deg."""
    print("\n -> Sending TILT 90 - servo should be horizontal.")
    cmd.tilt(90)
    time.sleep(OBSERVE_S)


@pytest.mark.hardware
def test_tilt_max_position(cmd: Commander) -> None:
    """Tilt servo should move to 180 deg physical endpoint (90 deg up)."""
    print(f"\n -> Sending TILT MAX ({TILT_TICKS_MAX} ticks) - should be 90 deg up.")
    cmd.tilt(180)
    time.sleep(OBSERVE_S)


@pytest.mark.hardware
def test_tilt_sweep(cmd: Commander) -> None:
    """Sweep tilt from 0 to 180 deg in steps to verify linearity."""
    print("\n -> Sweeping tilt 0 -> 180 deg in 45 deg steps.")
    for deg in range(0, 181, 45):
        print(f"    TILT {deg} deg")
        cmd.tilt(deg)
        time.sleep(1.5)
    cmd.tilt(90)  # return to horizontal
    time.sleep(1.0)
